#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from sync_agent_mac import api_request, DEFAULT_API_URL  # noqa: E402


def main() -> int:
    result = api_request('POST', '/api/apple/mappings', {'action': 'cleanup_orphans'}, base_url=DEFAULT_API_URL)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
