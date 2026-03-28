#!/usr/bin/env python3
from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / 'agent-runtime' / 'aigtd'
LIVE_DIR = Path('/root/.openclaw/workspace/agents/aigtd')
FILES = ['PROMPT.md', 'OPERATING-GUIDE.md', 'MEMORY.md']


def sync_file(src: Path, dst: Path, dry_run: bool = False) -> str:
    if not src.exists():
        return f'skip {src.name}: source missing'
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.is_symlink():
        target = dst.resolve()
        if target == src.resolve():
            return f'linked {src.name} -> {src}'
        return f'skip {src.name}: live file is symlink to {target}, please inspect manually'

    if dst.exists() and filecmp.cmp(src, dst, shallow=False):
        return f'unchanged {src.name}'
    if not dry_run:
        shutil.copy2(src, dst)
    return f'updated {src.name}'


def main() -> int:
    parser = argparse.ArgumentParser(description='Sync AIGTD runtime files from repo to live agent directory')
    parser.add_argument('--dry-run', action='store_true', help='show changes without copying')
    args = parser.parse_args()

    print(f'source: {SOURCE_DIR}')
    print(f'live:   {LIVE_DIR}')
    print('note: current preferred mode is single-source + symlink; this script is now a fallback repair tool.')
    for name in FILES:
        print(sync_file(SOURCE_DIR / name, LIVE_DIR / name, dry_run=args.dry_run))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
