"""Run the exact signed original-client build on a real Android emulator.

No Unity or C# doubles. A running process is not a gameplay pass.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import time

apk, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(exist_ok=True)
package = 'com.userjoy.ujjsgc.jp'
activity = package + '/com.unity3d.player.UnityPlayerActivity'
expected = '499027020bc20b2b9a829ab3889b78544523ae241e0b599825e62710abf4b61f'

def adb(*args, timeout=60, check=True):
    p = subprocess.run(['adb', *args], capture_output=True, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(p.stderr.decode(errors='replace') or p.stdout.decode(errors='replace'))
    return p

def sanitized(raw):
    lines = raw.decode(errors='replace').splitlines()
    sensitive = re.compile(r'(?i)authorization|bearer\s|api.?key\s*[:=]|(?:access|refresh|auth|registration)[_ -]?token\s*[:=]|password\s*[:=]')
    return '\n'.join('[redacted credential-like log line]' if sensitive.search(s) else s for s in lines) + '\n'

report = {'apk_sha256': None, 'android_sdk': None, 'installed': False,
          'gameplay_verified': False, 'capture_stages': [], 'errors': []}
log_proc = None
log_file = None
try:
    h = hashlib.sha256()
    with apk.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    report['apk_sha256'] = h.hexdigest()
    assert h.hexdigest() == expected
    props = {}
    for key in ('ro.build.version.release', 'ro.build.version.sdk', 'ro.product.cpu.abilist',
                'ro.dalvik.vm.native.bridge', 'sys.boot_completed'):
        props[key] = adb('shell', 'getprop', key).stdout.decode().strip()
    report['device'] = props
    report['android_sdk'] = int(props['ro.build.version.sdk'])
    assert report['android_sdk'] >= 29 and props['sys.boot_completed'] == '1'
    assert 'arm64-v8a' in props['ro.product.cpu.abilist']
    adb('root')
    time.sleep(2)
    adb('wait-for-device')
    adb('shell', 'settings', 'put', 'system', 'screen_off_timeout', '2147483647')
    install = adb('install', '-r', '-g', str(apk), timeout=240)
    (out / 'install.txt').write_text(sanitized(install.stdout + install.stderr))
    assert b'Success' in install.stdout
    report['installed'] = True
    uid_text = adb('shell', 'pm', 'list', 'packages', '-U', package).stdout.decode()
    uid = re.search(r'uid:(\d+)', uid_text).group(1)
    report['uid'] = int(uid)
    # All game traffic is blocked while the device remains normally connected.
    # This verifies the single local route rather than changing phone Wi-Fi state.
    for tool in ('iptables', 'ip6tables'):
        adb('shell', tool, '-A', 'OUTPUT', '-m', 'owner', '--uid-owner', uid, '-j', 'REJECT')
    report['game_uid_external_traffic_blocked'] = True
    adb('logcat', '-c')
    raw_log = Path('/tmp/sgm-app-logcat.txt')
    log_file = raw_log.open('wb')
    # API 30's bundled logcat does not accept --uid on this image. Collect the
    # isolated emulator buffers and retain sanitized output, including startup.
    log_proc = subprocess.Popen(['adb', 'shell', 'logcat', '-b', 'all', '-v', 'threadtime'],
                                stdout=log_file, stderr=subprocess.STDOUT)
    time.sleep(1)
    if log_proc.poll() is not None:
        raise RuntimeError('Android logcat collector exited before app launch')
    launch = adb('shell', 'am', 'start', '-W', '-S', '-n', activity, timeout=90)
    (out / 'launch.txt').write_text(sanitized(launch.stdout + launch.stderr))
    started = time.monotonic()
    for stage in (15, 45, 90):
        time.sleep(max(0, stage - (time.monotonic() - started)))
        capture = {'seconds_after_launch': stage}
        try:
            png = adb('exec-out', 'screencap', '-p', timeout=30).stdout
            assert png.startswith(b'\x89PNG\r\n\x1a\n')
            (out / f'screen-{stage:03}.png').write_bytes(png)
            capture['screenshot'] = f'screen-{stage:03}.png'
        except Exception as e:
            capture['screenshot_error'] = str(e)
        capture['game_pid'] = adb('shell', 'pidof', package, check=False).stdout.decode().strip()
        capture['logcat_running'] = log_proc.poll() is None
        if not capture['logcat_running']:
            report['errors'].append('Android logcat collector exited during test')
        report['capture_stages'].append(capture)
        (out / 'runtime-report.json').write_text(json.dumps(report, indent=2) + '\n')
    (out / 'activity.txt').write_text(sanitized(adb('shell', 'dumpsys', 'activity', 'top').stdout))
    (out / 'package.txt').write_text(sanitized(adb('shell', 'dumpsys', 'package', package).stdout))
    assert log_proc.poll() is None, 'Android logcat collector did not survive test'
except Exception as e:
    report['errors'].append(str(e))
    raise
finally:
    if log_proc:
        log_proc.terminate()
        try:
            log_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            log_proc.kill()
    if log_file:
        log_file.close()
    raw = Path('/tmp/sgm-app-logcat.txt')
    if raw.exists():
        (out / 'game-logcat.txt').write_text(sanitized(raw.read_bytes()[-8 * 1024 * 1024:]))
    try:
        crash = adb('logcat', '-d', '-b', 'crash', timeout=30, check=False)
        (out / 'crash.txt').write_text(sanitized(crash.stdout[-2 * 1024 * 1024:]))
    except Exception as e:
        report['errors'].append('crash log: ' + str(e))
    (out / 'runtime-report.json').write_text(json.dumps(report, indent=2) + '\n')
