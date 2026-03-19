use scripting additions

-- Phase 1: export Apple Reminders completed events by resolving reminder->gtd_id from local map.
-- Usage:
--   osascript mac/export_completed_reminders_phase1.applescript /abs/path/to/output.json [/abs/path/to/local-map.json]
-- Notes:
--   1) No longer depends on [GTD_ID] marker in reminder body.
--   2) Primary match key is reminder title + list name from local sync map.
--   3) If completion date is unavailable, keep completed_at empty for compatibility.

on run argv
	if (count of argv) is 0 then error "Missing output json path"
	set outputPath to item 1 of argv
	if (count of argv) ≥ 2 then
		set localMapPath to item 2 of argv
	else
		set localMapPath to "/root/.openclaw/workspace/gtd-tasks/sync/apple-reminders-local-map.json"
	end if
	set rows to {}
	
	tell application "Reminders"
		repeat with oneList in every list
			set listName to name of oneList as text
			repeat with oneReminder in every reminder of oneList
				try
					if completed of oneReminder is true then
						set reminderName to name of oneReminder as text
						set completedAtText to my safeCompletedAt(oneReminder)
						set reminderKey to my buildReminderKey(listName, reminderName)
						set end of rows to (listName & tab & reminderName & tab & completedAtText & tab & reminderKey)
					end if
				on error
					-- skip single reminder errors for robustness
				end try
			end repeat
		end repeat
	end tell
	
	my writeJson(outputPath, localMapPath, rows)
	return "OK exported=" & (count of rows)
end run

on buildReminderKey(listName, reminderName)
	return listName & "\n" & reminderName
end buildReminderKey

on safeCompletedAt(oneReminder)
	try
		set completedDateValue to completion date of oneReminder
		if completedDateValue is missing value then return ""
		return my isoFromDate(completedDateValue)
	on error
		return ""
	end try
end safeCompletedAt

on isoFromDate(dateValue)
	set yearText to text -4 thru -1 of ("0000" & (year of dateValue as integer))
	set monthText to text -2 thru -1 of ("00" & (month of dateValue as integer))
	set dayText to text -2 thru -1 of ("00" & (day of dateValue as integer))
	set hoursText to text -2 thru -1 of ("00" & (hours of dateValue as integer))
	set minutesText to text -2 thru -1 of ("00" & (minutes of dateValue as integer))
	set secondsText to text -2 thru -1 of ("00" & (seconds of dateValue as integer))
	return yearText & "-" & monthText & "-" & dayText & "T" & hoursText & ":" & minutesText & ":" & secondsText
end isoFromDate

on writeJson(outputPath, localMapPath, rows)
	set pythonCmd to "/usr/bin/python3 - <<'PY' " & quoted form of outputPath & " " & quoted form of localMapPath & "\nimport json, sys\nfrom pathlib import Path\nout = sys.argv[1]\nmap_path = Path(sys.argv[2])\nlocal_map = {}\nif map_path.exists():\n    with map_path.open('r', encoding='utf-8') as f:\n        local_map = json.load(f)\nentries = local_map.get('entries', []) if isinstance(local_map, dict) else []\nkey_to_entry = {}\nfor entry in entries:\n    key = (entry.get('match_key') or '').strip()\n    if key and key not in key_to_entry:\n        key_to_entry[key] = entry\nrows = []\nfor raw in sys.stdin.read().splitlines():\n    if not raw.strip():\n        continue\n    parts = raw.split('\\t')\n    if len(parts) < 4:\n        continue\n    list_name, title, completed_at, reminder_key = parts[:4]\n    entry = key_to_entry.get(reminder_key)\n    if not entry:\n        continue\n    gtd_id = (entry.get('gtd_id') or '').strip()\n    if not gtd_id:\n        continue\n    event_id = f\"{gtd_id}::{list_name}::{title}::{completed_at}\"\n    rows.append({\n        'event_id': event_id,\n        'event_type': 'completed',\n        'source': 'apple_reminders_phase1_local_map',\n        'gtd_id': gtd_id,\n        'completed_at': completed_at,\n        'apple_list_name': list_name,\n        'title': title,\n        'match_key': reminder_key,\n    })\nwith open(out, 'w', encoding='utf-8') as f:\n    json.dump({\n        'version': '0.4.0-phase1-local-map',\n        'generated_at': None,\n        'local_map_path': str(map_path),\n        'events': rows,\n    }, f, ensure_ascii=False, indent=2)\n    f.write('\\n')\nPY"
	set payload to ""
	repeat with rowText in rows
		set payload to payload & rowText & linefeed
	end repeat
	do shell script "printf %s " & quoted form of payload & " | " & pythonCmd
end writeJson
