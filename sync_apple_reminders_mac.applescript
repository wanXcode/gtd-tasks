use scripting additions

-- GTD Tasks -> Apple Reminders sync bridge (macOS MVP+)
-- Usage:
--   osascript sync_apple_reminders_mac.applescript /absolute/path/to/apple-reminders-export.json

on run argv
	if (count of argv) is 0 then error "Missing export json path"
	set jsonPath to item 1 of argv
	set rows to my loadRows(jsonPath)
	set createdCount to 0
	set updatedCount to 0
	set movedCount to 0
	set dueAppliedCount to 0

	tell application "Reminders"
		repeat with rowText in rows
			if rowText is not "" then
				set parts to my splitByTab(rowText as text)
				if (count of parts) ≥ 7 then
					set gtdId to item 1 of parts
					set listName to item 2 of parts
					set reminderTitle to item 3 of parts
					set reminderBody to my replaceText(" ", linefeed, item 4 of parts)
					set dueDateText to item 5 of parts
					set existingListName to item 6 of parts
					set syncAction to item 7 of parts

					set foundData to my findReminderAnywhere(gtdId, reminderTitle)
					set reminderRef to item 1 of foundData
					set foundListName to item 2 of foundData

					if syncAction is "complete" then
						if reminderRef is not missing value then
							try
								set completed of reminderRef to true
							end try
							set updatedCount to updatedCount + 1
						end if
					else
						set targetListRef to my ensureListByName(listName)

						if reminderRef is missing value then
							set reminderRef to make new reminder with properties {name:reminderTitle, body:reminderBody} at end of reminders of targetListRef
							set createdCount to createdCount + 1
						else
							if foundListName is not listName then
								set movedReminder to make new reminder at end of reminders of targetListRef with properties {name:(name of reminderRef), body:(body of reminderRef)}
								try
									set completed of movedReminder to completed of reminderRef
								end try
								try
									set due date of movedReminder to due date of reminderRef
								end try
								delete reminderRef
								set reminderRef to movedReminder
								set movedCount to movedCount + 1
							end if
							set name of reminderRef to reminderTitle
							set body of reminderRef to reminderBody
							set updatedCount to updatedCount + 1
						end if

						if my applyDueDate(reminderRef, dueDateText) then
							set dueAppliedCount to dueAppliedCount + 1
						end if
					end if
				end if
			end if
		end repeat
	end tell
	return "OK created=" & createdCount & " updated=" & updatedCount & " moved=" & movedCount & " due=" & dueAppliedCount
end run

on loadRows(jsonPath)
	set pythonCmd to "/usr/bin/python3 - <<'PY' " & quoted form of jsonPath & "\nimport json, sys\npath = sys.argv[1]\nwith open(path, 'r', encoding='utf-8') as f:\n    data = json.load(f)\nfor t in data.get('tasks', []):\n    title = (t.get('title') or '').replace('\\n', ' ').strip()\n    notes = (t.get('reminder_notes') or '').replace('\\r\\n', '\\n')\n    list_name = (t.get('target_list') or 'Inbox').strip()\n    gtd_id = t.get('gtd_id') or ''\n    due_date = (t.get('due_date') or '').strip()\n    existing_list_name = (t.get('existing_list_name') or '').strip()\n    sync_action = (t.get('sync_action') or 'upsert').strip()\n    print(gtd_id + '\\t' + list_name + '\\t' + title + '\\t' + notes.replace('\\n', '\\u2028') + '\\t' + due_date + '\\t' + existing_list_name + '\\t' + sync_action)\nPY"
	return paragraphs of (do shell script pythonCmd)
end loadRows

on splitByTab(sourceText)
	set oldTids to AppleScript's text item delimiters
	set AppleScript's text item delimiters to tab
	set itemsList to text items of sourceText
	set AppleScript's text item delimiters to oldTids
	return itemsList
end splitByTab

on ensureListByName(listName)
	tell application "Reminders"
		repeat with oneList in every list
			if (name of oneList as text) is listName then return oneList
		end repeat
		return (make new list with properties {name:listName})
	end tell
end ensureListByName

on findReminderAnywhere(gtdId, reminderTitle)
	tell application "Reminders"
		repeat with oneList in every list
			repeat with oneReminder in every reminder of oneList
				try
					set bodyText to body of oneReminder as text
				on error
					set bodyText to ""
				end try
				if gtdId is not "" and bodyText contains ("[GTD_ID] " & gtdId) then return {oneReminder, name of oneList as text}
			end repeat
		end repeat

		if reminderTitle is not "" then
			repeat with oneList in every list
				repeat with oneReminder in every reminder of oneList
					if (name of oneReminder as text) is reminderTitle then return {oneReminder, name of oneList as text}
				end repeat
			end repeat
		end if
	end tell
	return {missing value, ""}
end findReminderAnywhere

on applyDueDate(targetReminder, dueDateText)
	if dueDateText is "" then return false
	try
		set y to (text 1 thru 4 of dueDateText) as integer
		set m to (text 6 thru 7 of dueDateText) as integer
		set d to (text 9 thru 10 of dueDateText) as integer
		set dueDateValue to current date
		set year of dueDateValue to y
		set month of dueDateValue to m
		set day of dueDateValue to d
		set time of dueDateValue to 43200
		tell application "Reminders"
			set due date of targetReminder to dueDateValue
		end tell
		return true
	on error
		return false
	end try
end applyDueDate

on replaceText(findText, replaceTextValue, sourceText)
	set oldTids to AppleScript's text item delimiters
	set AppleScript's text item delimiters to findText
	set textItems to every text item of sourceText
	set AppleScript's text item delimiters to replaceTextValue
	set newText to textItems as text
	set AppleScript's text item delimiters to oldTids
	return newText
end replaceText
