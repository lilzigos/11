"""Publish only this disposable emulator's evidence to its run-specific branch."""
from pathlib import Path
import os
import subprocess


def publish():
    run_number = os.environ['GITHUB_RUN_NUMBER']
    attempt = os.environ['GITHUB_RUN_ATTEMPT']
    assert run_number.isdigit() and attempt.isdigit()
    branch = f'sgm-android11-evidence-{run_number}-{attempt}'
    state = Path('/tmp/sgm-evidence-parent')
    parent = state.read_text().strip() if state.exists() else None
    env = dict(os.environ, GIT_INDEX_FILE='/tmp/sgm-evidence-index',
               GIT_AUTHOR_NAME='SGM runtime validation',
               GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com',
               GIT_COMMITTER_NAME='SGM runtime validation',
               GIT_COMMITTER_EMAIL='41898282+github-actions[bot]@users.noreply.github.com')

    def git(*args):
        return subprocess.check_output(['git', *args], env=env, timeout=90).decode().strip()

    git('read-tree', '--empty')
    git('add', '--', 'runtime-evidence')
    tree = git('write-tree')
    if parent and git('rev-parse', parent + '^{tree}') == tree:
        return
    args = ['commit-tree', tree, '-m', f'Android 11 evidence {run_number}, attempt {attempt}']
    if parent:
        args += ['-p', parent]
    commit = git(*args)
    git('push', 'origin', commit + ':refs/heads/' + branch)
    state.write_text(commit + '\n')


if __name__ == '__main__':
    publish()
