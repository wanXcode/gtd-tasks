-- GTD Tasks -> Apple Reminders sync bridge (macOS MVP)
-- Usage:
--   osascript sync_apple_reminders_mac.applescript /absolute/path/to/apple-reminders-export.json

on run argv
	if (count of argv) is 0 then
		error "Missing export json path"
	end if
	set jsonPath to item 1 of argv
	set pythonCmd to "/usr/bin/python3 - <<'PY' " & quoted form of jsonPath & "\nimport json, sys\npath = sys.argv[1]\nwith open(path, 'r', encoding='utf-8') as f:\n    data = json.load(f)\nfor t in data.get('tasks', []):\n    title = (t.get('title') or '').replace('\\n', ' ').strip()\n    notes = (t.get('reminder_notes') or '').replace('\\r\\n', '\\n')\n    list_name = (t.get('target_list') or 'Inbox').strip()\n    gtd_id = t.get('gtd_id') or ''\n    print(gtd_id + '\\t' + list_name + '\\t' + title + '\\t' + notes.replace('\\n', '\\u2028'))\nPY"
	set rows to paragraphs of (do shell script pythonCmd)
	
	tell application "Reminders"
		repeat with rowText in rows
			if rowText is "" then
				-- skip
			else
				set AppleScript's text item delimiters to tab
				set parts to text items of rowText
				set AppleScript's text item delimiters to ""
				if (count of parts) ≥ 4 then
					set gtdId to item 1 of parts
					set listName to item 2 of parts
					set reminderTitle to item 3 of parts
					set reminderBody to item 4 of parts
					set reminderBody to my replaceText(" ", linefeed, reminderBody)
					
					if not (exists list listName) then
						make new list with properties {name:listName}
					end if
					set targetList to list listName
					
					set existingReminder to missing value
					repeat with r in reminders of targetList
						try
							set bodyText to body of r
						on error
							set bodyText to ""
						end try
						if bodyText contains ("[GTD_ID] " & gtdId) then
							set existingReminder to r
							exit repeat
						end if
					end repeat
					
					if existingReminder is missing value then
						make new reminder at targetList with properties {name:reminderTitle, body:reminderBody}
					else
						set name of existingReminder to reminderTitle
						set body of existingReminder to reminderBody
					end if
				end if
			end if
		end repeat
	end tell
	return "OK"
end run

on replaceText(findText, replaceText, sourceText)
	set AppleScript's text item delimiters to findText
	set textItems to every text item of sourceText
	set AppleScript's text item delimiters to replaceText
	set newText to textItems as text
	set AppleScript's text item delimiters to ""
	return newText
end replaceText
