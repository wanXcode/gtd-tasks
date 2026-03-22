#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from apple_reminders_sync_lib import (  # noqa: E402
    GIT_SYNC_ALLOWED_PATHS,
    GIT_SYNC_COMMIT_ENV,
    GIT_SYNC_DRY_RUN_ENV,
    GIT_SYNC_PUSH_ENV,
    ROOT as LIB_ROOT,
    SyncError,
    bool_from_env,
    git_sync_export,
    setup_logger,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Commit/push Apple Reminders export files safely')
    parser.add_argument('--commit', action='store_true', help='stage + commit allowed sync files')
    parser.add_argument('--push', action='store_true', help='push after commit (implies commit)')
    parser.add_argument('--dry-run', action='store_true', help='show what would be staged/committed/pushed')
    parser.add_argument('--pretty', action='store_true', help='pretty-print JSON output')
    return parser


def dump(obj: Dict, pretty: bool = False) -> None:
    if pretty:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(obj, ensure_ascii=False))


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    logger = setup_logger('git_sync_export')

    enable_commit = args.commit or args.push or bool_from_env(GIT_SYNC_COMMIT_ENV, False)
    enable_push = args.push or bool_from_env(GIT_SYNC_PUSH_ENV, False)
    dry_run = args.dry_run or bool_from_env(GIT_SYNC_DRY_RUN_ENV, False)

    if enable_push:
        enable_commit = True

    result = git_sync_export(
        logger=logger,
        enable_commit=enable_commit,
        enable_push=enable_push,
        dry_run=dry_run,
    )
    dump(result, pretty=args.pretty)


if __name__ == '__main__':
    main()
