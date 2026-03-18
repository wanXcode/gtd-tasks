use scripting additions

-- Phase 1: export only Apple Reminders completed events that contain stable [GTD_ID] marker.
-- Usage:
--   osascript mac/export_completed_reminders_phase1.applescript /abs/path/to/output.json
-- Notes:
--   1) This is intentionally conservative: only completed reminders with [GTD_ID] xxx in body.
--   2) First version uses reminder name + completion date to build a best-effort event_id.
--   3) If your Reminders AppleScript dictionary exposes stable id/body/completion date fields, you can enrich here later.

on run argv
	if (count of argv) is 0 then error "Missing output json path"
	set outputPath to item 1 of argv
	set rows to {}
	
	tell application "Reminders"
		repeat with oneList in every list
			repeat with oneReminder in every reminder of oneList
				try
					if completed of oneReminder is true then
						set reminderName to name of oneReminder as text
						try
							set reminderBody to body of oneReminder as text
						on error
							set reminderBody to ""
						end try
						set gtdId to my extractGtdId(reminderBody)
						if gtdId is not "" then
							set completedAtText to my formatCompletionDate(oneReminder)
							set eventId to my buildEventId(gtdId, reminderName, completedAtText)
							set end of rows to (eventId & tab & gtdId & tab & completedAtText & tab & (name of oneList as text) & tab & reminderName)
						end if
					end if
				on error
					-- skip single reminder errors for robustness
				end try
			end repeat
		end repeat
	end tell
	
	my writeJson(outputPath, rows)
	return "OK exported=" & (count of rows)
end run

on extractGtdId(bodyText)
	set linesList to paragraphs of bodyText
	repeat with oneLine in linesList
		set lineText to oneLine as text
		if lineText starts with "[GTD_ID] " then
			return text 10 thru -1 of lineText
		end if
	end repeat
	return ""
end extractGtdId

on formatCompletionDate(oneReminder)
	try
		set d to completion date of oneReminder
		if d is missing value then return ""
		set y to year of d as integer
		set m to month of d as integer
		set dd to day of d as integer
		set hh to hours of d as integer
		set mm to minutes of d as integer
		set ss to seconds of d as integer
		return (y as text) & "-" & my pad2(m) & "-" & my pad2(dd) & "T" & my pad2(hh) & ":" & my pad2(mm) & ":" & my pad2(ss)
	on error
		return ""
	end try
end formatCompletionDate

on buildEventId(gtdId, reminderName, completedAtText)
	return gtdId & "::" & reminderName & "::" & completedAtText
end buildEventId

on pad2(n)
	set s to n as text
	if (length of s) is 1 then return "0" & s
	return s
end pad2

on writeJson(outputPath, rows)
	set pythonCmd to "/usr/bin/python3 - <<'PY' " & quoted form of outputPath & "\nimport json, sys\nout = sys.argv[1]\nrows = []\nfor raw in sys.stdin.read().splitlines():\n    if not raw.strip():\n        continue\n    parts = raw.split('\\t')\n    if len(parts) < 5:\n        continue\n    event_id, gtd_id, completed_at, list_name, title = parts[:5]\n    rows.append({\n        'event_id': event_id,\n        'event_type': 'completed',\n        'source': 'apple_reminders_phase1',\n        'gtd_id': gtd_id,\n        'completed_at': completed_at,\n        'apple_list_name': list_name,\n        'title': title,\n    })\nwith open(out, 'w', encoding='utf-8') as f:\n    json.dump({\n        'version': '0.4.0-phase1',\n        'generated_at': None,\n        'events': rows,\n    }, f, ensure_ascii=False, indent=2)\n    f.write('\\n')\nPY"
	set payload to ""
	repeat with rowText in rows
		set payload to payload & rowText & linefeed
	end repeat
	do shell script "printf %s " & quoted form of payload & " | " & pythonCmd
end writeJson
