#!/usr/bin/env python3
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SHANGHAI_TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parent.parent
TASKS_PATH = ROOT / "data" / "tasks.json"
MAPPING_PATH = ROOT / "config" / "apple_reminders_mapping.json"
DEFAULT_OUTPUT_PATH = ROOT / "sync" / "apple-reminders-export.json"


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


def get_field(task: Dict[str, Any], field: str) -> Any:
    return task.get(field)


def match_operator(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "equals":
        return actual == expected
    if operator == "in":
        return actual in ensure_list(expected)
    if operator == "contains_any":
        actual_list = [str(item) for item in ensure_list(actual)]
        expected_list = [str(item) for item in ensure_list(expected)]
        return any(item in actual_list for item in expected_list)
    if operator == "contains_all":
        actual_list = [str(item) for item in ensure_list(actual)]
        expected_list = [str(item) for item in ensure_list(expected)]
        return all(item in actual_list for item in expected_list)
    if operator == "contains_any_text":
        actual_text = normalize_text(actual)
        expected_list = [str(item) for item in ensure_list(expected)]
        return any(token in actual_text for token in expected_list)
    if operator == "not_in":
        return actual not in ensure_list(expected)
    raise ValueError(f"Unsupported operator: {operator}")


def evaluate_condition(task: Dict[str, Any], condition: Dict[str, Any]) -> bool:
    if "all" in condition:
        return all(evaluate_condition(task, item) for item in condition["all"])
    if "any" in condition:
        return any(evaluate_condition(task, item) for item in condition["any"])
    field = condition["field"]
    operator = condition["operator"]
    expected = condition.get("value")
    actual = get_field(task, field)
    return match_operator(actual, operator, expected)


def resolve_target_list(task: Dict[str, Any], mapping: Dict[str, Any], lists_by_id: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    rules = sorted(mapping.get("rules", []), key=lambda rule: rule.get("priority", 0), reverse=True)
    for rule in rules:
        if evaluate_condition(task, {"all": rule.get("all", [])}):
            list_def = lists_by_id[rule["target_list_id"]]
            return list_def, rule
    raise RuntimeError(f"No matching rule for task {task.get('id')}")


def render_template(template_lines: List[str], task: Dict[str, Any]) -> str:
    values = {
        "id": task.get("id", ""),
        "bucket": task.get("bucket", ""),
        "quadrant": task.get("quadrant", ""),
        "tags_csv": ", ".join(task.get("tags", []) or []),
        "updated_at": task.get("updated_at", ""),
        "note": task.get("note", "") or "",
    }
    rendered = []
    for line in template_lines:
        current = line
        for key, value in values.items():
            current = current.replace("{{" + key + "}}", str(value))
        rendered.append(current)
    while rendered and rendered[-1] == "":
        rendered.pop()
    return "\n".join(rendered)


def export_payload(tasks_doc: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
    lists = mapping.get("lists", [])
    lists_by_id = {item["id"]: item for item in lists}
    template_lines = mapping.get("export", {}).get("note_template", [])
    output_tasks = []

    for task in tasks_doc.get("tasks", []):
        if task.get("status") != "open":
            continue
        target_list, matched_rule = resolve_target_list(task, mapping, lists_by_id)
        output_tasks.append({
            "gtd_id": task.get("id"),
            "title": task.get("title"),
            "note": task.get("note", ""),
            "status": task.get("status"),
            "bucket": task.get("bucket"),
            "quadrant": task.get("quadrant"),
            "tags": task.get("tags", []),
            "updated_at": task.get("updated_at"),
            "target_list": target_list.get("name"),
            "target_list_id": target_list.get("id"),
            "target_list_status": target_list.get("status", "active"),
            "matched_rule_id": matched_rule.get("id") if matched_rule else None,
            "matched_rule_name": matched_rule.get("name") if matched_rule else None,
            "reminder_notes": render_template(template_lines, task),
        })

    generated_at = datetime.now(SHANGHAI_TZ).isoformat()
    return {
        "version": mapping.get("version", "0.3.0-draft"),
        "timezone": mapping.get("timezone", "Asia/Shanghai"),
        "generated_at": generated_at,
        "source": {
            "tasks_file": str(TASKS_PATH.relative_to(ROOT)),
            "mapping_file": str(MAPPING_PATH.relative_to(ROOT)),
            "business_date": tasks_doc.get("meta", {}).get("business_date"),
            "source_updated_at": tasks_doc.get("meta", {}).get("updated_at"),
        },
        "lists": lists,
        "tasks": output_tasks,
        "summary": {
            "exported_open_tasks": len(output_tasks),
            "total_source_tasks": len(tasks_doc.get("tasks", [])),
        },
    }


def main() -> None:
    tasks_doc = load_json(TASKS_PATH)
    mapping = load_json(MAPPING_PATH)
    payload = export_payload(tasks_doc, mapping)

    configured_output = mapping.get("export", {}).get("output_path")
    output_path = ROOT / configured_output if configured_output else DEFAULT_OUTPUT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Exported {payload['summary']['exported_open_tasks']} tasks -> {output_path}")


if __name__ == "__main__":
    main()
