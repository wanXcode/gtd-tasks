#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BRIDGE_PATH = ROOT / 'mac' / 'reminders-bridge'
DEFAULT_BACKEND = 'eventkit'


class ReminderBridgeError(RuntimeError):
    pass


class ReminderBridge:
    def __init__(self, backend: Optional[str] = None, bridge_path: Optional[Path] = None):
        self.backend = (backend or DEFAULT_BACKEND).strip().lower()
        self.bridge_path = Path(bridge_path) if bridge_path else Path(os.getenv('GTD_REMINDERS_BRIDGE_PATH', str(DEFAULT_BRIDGE_PATH)))

    def use_eventkit(self) -> bool:
        return self.backend == 'eventkit'

    def run_eventkit(self, action: str, payload: Optional[Dict[str, Any]] = None, timeout: int = 60) -> Dict[str, Any]:
        if not self.bridge_path.exists():
            raise ReminderBridgeError(f'EventKit bridge not found: {self.bridge_path}')

        cmd = [str(self.bridge_path), action]
        if payload is not None:
            cmd.extend(['--input-json', json.dumps(payload, ensure_ascii=False)])

        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        stdout = (completed.stdout or '').strip()
        stderr = (completed.stderr or '').strip()

        if completed.returncode != 0:
            raise ReminderBridgeError(stderr or stdout or f'EventKit bridge failed: action={action} code={completed.returncode}')

        if not stdout:
            return {'success': True, 'action': action, 'stdout': '', 'stderr': stderr}

        try:
            data = json.loads(stdout)
            if isinstance(data, dict):
                return data
            return {'success': True, 'action': action, 'data': data, 'stderr': stderr}
        except json.JSONDecodeError:
            return {'success': True, 'action': action, 'stdout': stdout, 'stderr': stderr}
