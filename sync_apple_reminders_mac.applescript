use scripting additions

-- GTD Tasks -> Apple Reminders sync bridge (macOS MVP+)
-- Usage:
--   osascript sync_apple_reminders_mac.applescript /absolute/path/to/apple-reminders-export.json

on run argv
	if (count of argv) is 0 then error "Missing export json path"
	set jsonPath to item 1 of argv
	set scriptPath to POSIX path of (path to me)
	set repoRoot to do shell script "cd " & quoted form of (do shell script "dirname " & quoted form of scriptPath) & " && pwd"
	set localMapPath to repoRoot & "/sync/apple-reminders-local-map.json"
	set rows to my loadRows(jsonPath)
	set createdCount to 0
	set updatedCount to 0
	set movedCount to 0
	set dueAppliedCount to 0
	set localMapRows to {}

	tell application "Reminders"
		repeat with rowText in rows
			if rowText is not "" then
				set parts to my splitByTab(rowText as text)
				if (count of parts) >= 7 then
					set gtdId to item 1 of parts
					set listName to item 2 of parts
					set reminderTitle to item 3 of parts
					set reminderNotes to my replaceText(" ", linefeed, item 4 of parts)
					set reminderBody to my composeReminderBody(gtdId, reminderNotes)
					set dueDateText to item 5 of parts
					set existingListName to item 6 of parts
					set syncAction to item 7 of parts

					set foundData to my findReminderAnywhere(gtdId, listName, reminderTitle)
					set reminderRef to item 1 of foundData
					set foundListName to item 2 of foundData

					if syncAction is "complete" then
						if reminderRef is not missing value then
							try
								tell application "Reminders"
									set completed of reminderRef to true
									set completion date of reminderRef to current date
								end tell
							on error errMsg number errNum
								error "complete failed for " & gtdId & ": " & errMsg & " (" & errNum & ")"
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
						set end of localMapRows to my buildLocalMapRow(gtdId, listName, reminderTitle)
					end if
				end if
			end if
		end repeat
	end tell
	my writeLocalMap(localMapPath, localMapRows)
	return "OK created=" & createdCount & " updated=" & updatedCount & " moved=" & movedCount & " due=" & dueAppliedCount & " mapped=" & (count of localMapRows)
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
		if (exists list listName) then
			return list listName
		end if
		return (make new list with properties {name:listName})
	end tell
end ensureListByName

on findReminderAnywhere(gtdId, targetListName, reminderTitle)
	tell application "Reminders"
		set allLists to every list
		repeat with oneList in allLists
			set listNameText to name of oneList as text
			set reminderItems to every reminder of oneList
			repeat with oneReminder in reminderItems
				try
					set bodyText to body of oneReminder as text
				on error
					set bodyText to ""
				end try
				if gtdId is not "" and bodyText contains ("[GTD_ID] " & gtdId) then return {contents of oneReminder, listNameText}
			end repeat
		end repeat

		if targetListName is not "" and reminderTitle is not "" then
			try
				if exists list targetListName then
					set targetListRef to list targetListName
					set reminderItems to every reminder of targetListRef
					repeat with oneReminder in reminderItems
						if (name of oneReminder as text) is reminderTitle then return {contents of oneReminder, targetListName}
					end repeat
				end if
			on error
				-- ignore missing list
			end try
		end if

		if reminderTitle is not "" then
			repeat with oneList in allLists
				set listNameText to name of oneList as text
				set reminderItems to every reminder of oneList
				repeat with oneReminder in reminderItems
					if (name of oneReminder as text) is reminderTitle then return {contents of oneReminder, listNameText}
				end repeat
			end repeat
		end if
	end tell
	return {missing value, ""}
end findReminderAnywhere

on buildLocalMapRow(gtdId, listName, reminderTitle)
	set matchKey to listName & "\n" & reminderTitle
	return gtdId & tab & listName & tab & reminderTitle & tab & matchKey
end buildLocalMapRow

on composeReminderBody(gtdId, notesText)
	set cleanNotes to my stripGtdMarker(notesText)
	if gtdId is "" then return cleanNotes
	set markerLine to "[GTD_ID] " & gtdId
	if cleanNotes is "" then return markerLine
	return markerLine & linefeed & linefeed & cleanNotes
end composeReminderBody

on stripGtdMarker(bodyText)
	if bodyText is "" then return ""
	set marker to "[GTD_ID]"
	if bodyText does not contain marker then return bodyText
	set paragraphsList to paragraphs of bodyText
	set keptParagraphs to {}
	repeat with oneParagraph in paragraphsList
		set paragraphText to oneParagraph as text
		if paragraphText does not start with marker then set end of keptParagraphs to paragraphText
	end repeat
	set rebuiltText to ""
	repeat with i from 1 to count of keptParagraphs
		set rebuiltText to rebuiltText & item i of keptParagraphs
		if i is less than (count of keptParagraphs) then set rebuiltText to rebuiltText & linefeed
	end repeat
	repeat while rebuiltText begins with linefeed
		set rebuiltText to text 2 thru -1 of rebuiltText
	end repeat
	repeat while rebuiltText ends with linefeed
		if (length of rebuiltText) is 1 then
			set rebuiltText to ""
		else
			set rebuiltText to text 1 thru -2 of rebuiltText
		end if
	end repeat
	return rebuiltText
end stripGtdMarker

on writeLocalMap(localMapPath, rows)
	set entriesJson to ""
	set seenKeys to {}
	repeat with rowText in rows
		set rawText to rowText as text
		if rawText is not "" then
			set parts to my splitByTab(rawText)
			if (count of parts) ≥ 4 then
				set gtdId to item 1 of parts
				set listName to item 2 of parts
				set reminderTitle to item 3 of parts
				set matchKey to item 4 of parts
				set dedupKey to gtdId & "||" & matchKey
				if seenKeys does not contain dedupKey then
					set end of seenKeys to dedupKey
					set oneEntry to "{\"gtd_id\":\"" & my jsonEscape(gtdId) & "\",\"list_name\":\"" & my jsonEscape(listName) & "\",\"title\":\"" & my jsonEscape(reminderTitle) & "\",\"match_key\":\"" & my jsonEscape(matchKey) & "\"}"
					if entriesJson is "" then
						set entriesJson to oneEntry
					else
						set entriesJson to entriesJson & "," & oneEntry
					end if
				end if
			end if
		end if
	end repeat
	set jsonText to "{\"version\":\"0.4.0-phase1-local-map\",\"generated_at\":null,\"match_strategy\":\"list_name+title\",\"entries\":[" & entriesJson & "]}"
	do shell script "mkdir -p " & quoted form of POSIX path of (do shell script "dirname " & quoted form of localMapPath) & " && /usr/bin/printf %s " & quoted form of jsonText & " > " & quoted form of localMapPath
end writeLocalMap

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

on jsonEscape(inputText)
	set t to inputText as text
	set t to my replaceText("\\", "\\\\", t)
	set t to my replaceText("\"", "\\\"", t)
	set t to my replaceText(return, "\\n", t)
	set t to my replaceText(linefeed, "\\n", t)
	set t to my replaceText(tab, "\\t", t)
	return t
end jsonEscape

on replaceText(findText, replaceTextValue, sourceText)
	set oldTids to AppleScript's text item delimiters
	set AppleScript's text item delimiters to findText
	set textItems to every text item of sourceText
	set AppleScript's text item delimiters to replaceTextValue
	set newText to textItems as text
	set AppleScript's text item delimiters to oldTids
	return newText
end replaceText
