#!/usr/bin/env python3
"""Install or inspect non-blocking subagent hooks for Codex and Claude Code."""
import argparse
import json
import os
from pathlib import Path
import shlex
import stat
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / 'hooks' / 'subagent_events.py'
EVENTS = ('SessionStart', 'SessionEnd', 'SubagentStart', 'SubagentStop')


def add_hooks(document, provider):
    if not isinstance(document, dict):
        raise ValueError('configuration must be a JSON object')
    hooks = document.setdefault('hooks', {})
    if not isinstance(hooks, dict):
        raise ValueError('hooks must be a JSON object')
    command = f'python3 {shlex.quote(str(BRIDGE))} {provider}'
    added = []
    for event in EVENTS:
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            raise ValueError(f'{event} must be a list')
        if any(hook.get('command') == command for group in groups if isinstance(group, dict) for hook in group.get('hooks', []) if isinstance(hook, dict)):
            continue
        groups.append({'hooks': [{'type': 'command', 'command': command, 'timeout': 5}]})
        added.append(event)
    return added


def prepare(path, provider):
    original = path.read_bytes() if path.exists() else None
    document = json.loads(original) if original is not None else {}
    added = add_hooks(document, provider)
    return original, (json.dumps(document, indent=2, ensure_ascii=False) + '\n').encode(), added


def write(path, original, content):
    if (path.read_bytes() if path.exists() else None) != original:
        raise RuntimeError(f'{path} changed while preparing; no overwrite performed')
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd, temp = tempfile.mkstemp(prefix='.iris-hook-', dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb') as output:
            output.write(content)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    home = Path.home()
    targets = [(home / '.codex/hooks.json', 'codex'), (home / '.claude/settings.json', 'claude')]
    plans = [(path, provider, *prepare(path, provider)) for path, provider in targets]
    for path, provider, original, content, added in plans:
        print(f'{provider}: {", ".join(added) if added else "already installed"}')
        if args.apply and added:
            write(path, original, content)
    if not args.apply:
        print('Preview only. Run with --apply to install.')


if __name__ == '__main__':
    main()
