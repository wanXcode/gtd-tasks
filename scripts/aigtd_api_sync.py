#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXECUTOR = ROOT / 'scripts' / 'aigtd_executor.py'


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Backward-compatible wrapper for AIGTD controlled executor')
    sub = p.add_subparsers(dest='cmd', required=True)

    add = sub.add_parser('add')
    add.add_argument('title')
    add.add_argument('--bucket', default='future', choices=['today', 'tomorrow', 'future', 'archive'])
    add.add_argument('--quadrant', default='q2', choices=['q1', 'q2', 'q3', 'q4'])
    add.add_argument('--note')
    add.add_argument('--category', choices=['inbox', 'project', 'next_action', 'waiting_for', 'maybe'])
    add.add_argument('--tags', nargs='*')
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    cmd = ['python3', str(EXECUTOR), 'add', args.title, '--bucket', args.bucket, '--quadrant', args.quadrant]
    if args.note:
        cmd += ['--note', args.note]
    if args.category:
        cmd += ['--category', args.category]
    if args.tags:
        cmd += ['--tags', *args.tags]
    subprocess.run(cmd, check=True)


if __name__ == '__main__':
    main()
