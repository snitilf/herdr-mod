#!/usr/bin/env python3
"""Copy tracked Herdr assets to the live configuration, with drift detection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
HERDR = Path.home() / '.config/herdr-app'
CODEX = Path.home() / '.codex/themes'
MANIFEST = ROOT / '.sync-state.json'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def files():
    result = []
    for folder in ('mods', 'themes', 'fonts', 'layouts'):
        for src in sorted((ROOT / folder).rglob('*')):
            if src.is_file() and src.name not in ('OFL.txt', 'jsconfig.json', 'gpui-kit.d.ts'):
                result.append((src, HERDR / src.relative_to(ROOT)))
    for src in sorted((ROOT / 'codex-themes').glob('*.tmTheme')):
        result.append((src, CODEX / src.name))
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='copy source files after checking for drift')
    args = parser.parse_args()
    state = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    pending, conflicts = [], []
    for src, dest in files():
        name = str(src.relative_to(ROOT))
        local, live, previous = digest(src), digest(dest), state.get(name)
        if live == local:
            continue
        if live is not None and (previous is None or live != previous):
            conflicts.append(name)
        else:
            pending.append((name, src, dest))
    if conflicts:
        print('Live files changed outside the source folder:')
        for name in conflicts:
            print('  ' + name)
        print('Compare and reconcile these files before syncing. No files were copied.')
        return 1
    if not args.apply:
        print('Ready to copy:' if pending else 'Source and live files match.')
        for name, _, _ in pending:
            print('  ' + name)
        return 0
    for name, src, dest in pending:
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = dest.with_name('.' + dest.name + '.herdr-sync-tmp')
        shutil.copyfile(src, temp)
        os.replace(temp, dest)
        print('Copied ' + name)
    new_state = {str(src.relative_to(ROOT)): digest(src) for src, _ in files()}
    MANIFEST.write_text(json.dumps(new_state, indent=2, sort_keys=True) + '\n')
    print('Sync complete.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
