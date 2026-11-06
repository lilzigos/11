"""Record only allowlisted CI metadata, with no credential/environment dump."""
from pathlib import Path
import json
import os

out = Path('runtime-evidence')
out.mkdir(exist_ok=True)
status = {key: os.environ.get(key) for key in (
    'GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_NUMBER', 'GITHUB_RUN_ATTEMPT',
    'DIAGNOSTIC_STATUS')}
status['gameplay_verified'] = False
status['scope'] = 'Native Android startup diagnostic; screenshots and logs require review.'
(out / 'workflow-status.json').write_text(json.dumps(status, indent=2) + '\n')
