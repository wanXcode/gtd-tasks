#!/usr/bin/env python3
"""Pull current task set from server API into local data/tasks.json cache.

Phase 1 scaffold only:
- keeps render_views.py compatibility path alive
- avoids forcing render layer to read API directly
- can later evolve to incremental cache refresh via /api/changes
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from task_repository import ApiTaskRepository, RepositoryError  # noqa: E402

DATA = ROOT / 'data' / 'tasks.json'


def dump_cache(items, path: Path):
    payload = {
        'version': '0.2.1-cache',
        'meta': {
            'source': 'api-cache',
            'count': len(items),
        },
        'tasks': items,
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write('\n')



def build_parser():
    parser = argparse.ArgumentParser(description='Pull GTD tasks from API into local cache file')
    parser.add_argument('--base-url', help='API base url; fallback to GTD_API_BASE_URL')
    parser.add_argument('--output', default=str(DATA), help='cache file path, default data/tasks.json')
    return parser



def main():
    args = build_parser().parse_args()
    try:
        repo = ApiTaskRepository(base_url=args.base_url)
        items = repo.list_tasks()
    except RepositoryError as exc:
        raise SystemExit(str(exc)) from exc
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    dump_cache(items, output)
    print(f'cached: {len(items)} task(s) -> {output}')


if __name__ == '__main__':
    main()
