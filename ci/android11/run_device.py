"""Run the exact signed original-client build on a real Android emulator.

No Unity or C# doubles. A running process is not a gameplay pass.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import time

from device_controls import validate
from publish_evidence import publish

apk, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(exist_ok=True)
package = 'com.userjoy.ujjsgc.jp'
activity = package + '/com.unity3d.player.UnityPlayerActivity'
expected = 'b849c12f19f518655e4efea5941896dd3712c80b0a3c55d3c67a56b033d6bb8d'

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

def snapshot_logs():
    if log_file:
        log_file.flush()
    raw = Path('/tmp/sgm-app-logcat.txt')
    if raw.exists():
        log_text = sanitized(raw.read_bytes()[-8 * 1024 * 1024:])
        (out / 'game-logcat.txt').write_text(log_text)
        report['lua_exception_messages'] = sorted(set(report.get('lua_exception_messages', [])) | set(
            line.split('LuaException:', 1)[1].strip() for line in log_text.splitlines()
            if 'LuaException:' in line))[:30]
        report['offline_adapters_initialized'] = report.get('offline_adapters_initialized', False) or 'Original client offline adapters installed' in log_text
    (out / 'runtime-report.json').write_text(json.dumps(report, indent=2) + '\n')

def take_capture(name):
    png = adb('exec-out', 'screencap', '-p', timeout=30).stdout
    assert png.startswith(b'\x89PNG\r\n\x1a\n')
    (out / name).write_bytes(png)
    return name

def interactive(seconds):
    run_id = os.environ['GITHUB_RUN_ID']
    branch = 'refs/heads/sgm-android11-control-' + run_id
    report['control'] = {'branch': branch, 'last_sequence': 0, 'results': [], 'active': True}
    snapshot_logs()
    publish()
    deadline = time.monotonic() + seconds
    seen_document = None
    done = False
    while time.monotonic() < deadline and not done:
        assert log_proc.poll() is None, 'Android logger exited during interactive test'
        p = subprocess.run(['git', 'fetch', '--no-tags', 'origin', branch],
                           capture_output=True, timeout=40)
        if p.returncode:
            time.sleep(5)
            continue
        raw = subprocess.check_output(['git', 'show', 'FETCH_HEAD:controls.json'], timeout=10)
        if raw == seen_document:
            time.sleep(5)
            continue
        seen_document = raw
        result = {}
        try:
            assert len(raw) <= 16384, 'Oversized control document'
            doc = json.loads(raw)
            commands = validate(doc, run_id, report['control']['last_sequence'] + 1)
            result['sequence'] = doc['sequence']
            result['actions'] = doc['actions']
            # Consume the sequence before actions: a failed input is never replayed.
            report['control']['last_sequence'] = doc['sequence']
            for step, command in enumerate(commands):
                if command[0] == 'input':
                    adb('shell', *command)
                    time.sleep(0.5)
                elif command[0] == 'wait':
                    time.sleep(int(command[1]))
                elif command[0] == 'restart':
                    adb('shell', 'am', 'force-stop', package)
                    adb('shell', 'am', 'start', '-W', '-n', activity)
                    time.sleep(10)
                elif command[0] == 'capture':
                    take_capture(f'input-{doc["sequence"]:03}-{step:02}.png')
                elif command[0] == 'finish':
                    done = True
            time.sleep(2)
            result['screenshot'] = take_capture(f'input-{doc["sequence"]:03}-final.png')
            result['status'] = 'executed'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        report['control']['results'].append(result)
        snapshot_logs()
        publish()
    report['control']['active'] = False
    report['control']['end_reason'] = 'finish command' if done else 'time limit'
    snapshot_logs()
    publish()

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
        snapshot_logs()
        if stage == 90:
            (out / 'startup-logcat.txt').write_bytes((out / 'game-logcat.txt').read_bytes())
        publish()
    interactive_seconds = int(os.environ.get('SGM_INTERACTIVE_SECONDS', '0'))
    assert 0 <= interactive_seconds <= 900
    if interactive_seconds:
        interactive(interactive_seconds)
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
