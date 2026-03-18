#!/usr/bin/env python3
import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from apple_reminders_sync_lib import (  # noqa: E402
    EXPORT_PATH as DEFAULT_OUTPUT_PATH,
    MAPPING_PATH,
    TASKS_PATH,
    build_incremental_tasks,
    derive_export_output_path,
    load_state,
    mark_exported_tasks,
    now_iso,
    save_state,
    setup_logger,
    update_state_from_tasks,
)

SHANGHAI_TZ = timezone(timedelta(hours=8))


def load_json(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, list):
        return ' '.join(str(item) for item in value)
    return str(value)


def get_field(task: Dict[str, Any], field: str) -> Any:
    return task.get(field)


def match_operator(actual: Any, operator: str, expected: Any) -> bool:
    if operator == 'equals':
        return actual == expected
    if operator == 'in':
        return actual in ensure_list(expected)
    if operator == 'contains_any':
        actual_list = [str(item) for item in ensure_list(actual)]
        expected_list = [str(item) for item in ensure_list(expected)]
        return any(item in actual_list for item in expected_list)
    if operator == 'contains_all':
        actual_list = [str(item) for item in ensure_list(actual)]
        expected_list = [str(item) for item in ensure_list(expected)]
        return all(item in actual_list for item in expected_list)
    if operator == 'contains_any_text':
        actual_text = normalize_text(actual)
        expected_list = [str(item) for item in ensure_list(expected)]
        return any(token in actual_text for token in expected_list)
    if operator == 'not_in':
        return actual not in ensure_list(expected)
    raise ValueError(f'Unsupported operator: {operator}')


def evaluate_condition(task: Dict[str, Any], condition: Dict[str, Any]) -> bool:
    if 'all' in condition:
        return all(evaluate_condition(task, item) for item in condition['all'])
    if 'any' in condition:
        return any(evaluate_condition(task, item) for item in condition['any'])
    field = condition['field']
    operator = condition['operator']
    expected = condition.get('value')
    actual = get_field(task, field)
    return match_operator(actual, operator, expected)


def resolve_target_list(task: Dict[str, Any], mapping: Dict[str, Any], lists_by_id: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    rules = sorted(mapping.get('rules', []), key=lambda rule: rule.get('priority', 0), reverse=True)
    for rule in rules:
        if evaluate_condition(task, {'all': rule.get('all', [])}):
            list_def = lists_by_id[rule['target_list_id']]
            return list_def, rule
    raise RuntimeError(f"No matching rule for task {task.get('id')}")


def render_template(template_lines: List[str], task: Dict[str, Any]) -> str:
    values = {
        'id': task.get('id', ''),
        'bucket': task.get('bucket', ''),
        'quadrant': task.get('quadrant', ''),
        'category': task.get('category', ''),
        'status': task.get('status', ''),
        'tags_csv': ', '.join(task.get('tags', []) or []),
        'updated_at': task.get('updated_at', ''),
        'note': task.get('note', '') or '',
    }
    rendered = []
    for line in template_lines:
        current = line
        for key, value in values.items():
            current = current.replace('{{' + key + '}}', str(value))
        rendered.append(current)
    while rendered and rendered[-1] == '':
        rendered.pop()
    return '\n'.join(rendered)


def derive_due_date(task: Dict[str, Any], business_date: Optional[str]) -> Optional[str]:
    title = task.get('title', '') or ''
    note = task.get('note', '') or ''
    text = f'{title} {note}'

    base_date = None
    if business_date:
        try:
            base_date = datetime.strptime(business_date, '%Y-%m-%d').date()
        except ValueError:
            base_date = None

    explicit = re.search(r'(20\d{2}-\d{2}-\d{2})', text)
    if explicit:
        return explicit.group(1)

    if base_date is None:
        return None

    if '明天' in text or task.get('bucket') == 'tomorrow':
        return (base_date + timedelta(days=1)).isoformat()
    if '今天' in text or task.get('bucket') == 'today':
        return base_date.isoformat()
    return None


def export_payload(tasks_doc: Dict[str, Any], mapping: Dict[str, Any], selected_tasks: Optional[List[Dict[str, Any]]] = None, changed_only: bool = False, requested_task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    lists = mapping.get('lists', [])
    lists_by_id = {item['id']: item for item in lists}
    template_lines = mapping.get('export', {}).get('note_template', [])
    business_date = tasks_doc.get('meta', {}).get('business_date')
    source_tasks = selected_tasks if selected_tasks is not None else list(tasks_doc.get('tasks', []))
    output_tasks = []

    for task in source_tasks:
        if task.get('status') != 'open':
            continue
        target_list, matched_rule = resolve_target_list(task, mapping, lists_by_id)
        output_tasks.append({
            'gtd_id': task.get('id'),
            'title': task.get('title'),
            'note': task.get('note', ''),
            'status': task.get('status'),
            'bucket': task.get('bucket'),
            'quadrant': task.get('quadrant'),
            'category': task.get('category'),
            'tags': task.get('tags', []),
            'updated_at': task.get('updated_at'),
            'sync_version': task.get('sync_version'),
            'target_list': target_list.get('name'),
            'target_list_id': target_list.get('id'),
            'target_list_status': target_list.get('status', 'active'),
            'matched_rule_id': matched_rule.get('id') if matched_rule else None,
            'matched_rule_name': matched_rule.get('name') if matched_rule else None,
            'due_date': derive_due_date(task, business_date),
            'reminder_notes': render_template(template_lines, task),
        })

    generated_at = datetime.now(SHANGHAI_TZ).isoformat()
    return {
        'version': mapping.get('version', '0.4.0-a'),
        'timezone': mapping.get('timezone', 'Asia/Shanghai'),
        'generated_at': generated_at,
        'source': {
            'tasks_file': str(TASKS_PATH.relative_to(ROOT)),
            'mapping_file': str(MAPPING_PATH.relative_to(ROOT)),
            'business_date': tasks_doc.get('meta', {}).get('business_date'),
            'source_updated_at': tasks_doc.get('meta', {}).get('updated_at'),
            'requested_task_ids': requested_task_ids or [],
            'changed_only': changed_only,
        },
        'lists': lists,
        'tasks': output_tasks,
        'summary': {
            'exported_open_tasks': len(output_tasks),
            'total_source_tasks': len(tasks_doc.get('tasks', [])),
            'selected_source_tasks': len(source_tasks),
        },
    }


def build_parser():
    parser = argparse.ArgumentParser(description='Export Apple Reminders sync payload')
    parser.add_argument('--task-id', action='append', dest='task_ids', help='仅导出指定 task id，可重复传入；未显式传 --output 时默认写入 sync/tmp/ 下的临时文件')
    parser.add_argument('--changed-only', action='store_true', help='仅导出发生变化的任务；未显式传 --output 时默认写入共享 sync/apple-reminders-export.json')
    parser.add_argument('--output', type=Path, help='导出路径；不传时：full/changed-only 写 sync/apple-reminders-export.json，单任务导出写 sync/tmp/ 临时文件')
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    logger = setup_logger('export_apple_reminders_sync')

    tasks_doc = load_json(TASKS_PATH)
    mapping = load_json(MAPPING_PATH)
    state = load_state()
    changed_ids = update_state_from_tasks(state, tasks_doc)

    selected_tasks = build_incremental_tasks(tasks_doc, task_ids=args.task_ids, changed_only=args.changed_only, state=state)
    payload = export_payload(
        tasks_doc,
        mapping,
        selected_tasks=selected_tasks,
        changed_only=args.changed_only,
        requested_task_ids=list(args.task_ids or []),
    )

    output_path = derive_export_output_path(task_ids=args.task_ids, changed_only=args.changed_only, output_path=args.output)
    if not args.output and not args.task_ids and not args.changed_only:
        output_path = Path(mapping.get('export', {}).get('output_path') or DEFAULT_OUTPUT_PATH)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write('\n')

    exported_at = payload.get('generated_at') or now_iso()
    state['last_export'] = {
        'at': exported_at,
        'output_path': str(output_path),
        'task_count': len(payload.get('tasks', [])),
        'requested_task_ids': list(args.task_ids or []),
        'changed_only': bool(args.changed_only),
        'changed_ids': changed_ids,
    }
    mark_exported_tasks(state, payload.get('tasks', []), exported_at)
    save_state(state)

    logger.info('Exported %s tasks -> %s', payload['summary']['exported_open_tasks'], output_path)
    print(f"Exported {payload['summary']['exported_open_tasks']} tasks -> {output_path}")


if __name__ == '__main__':
    main()
