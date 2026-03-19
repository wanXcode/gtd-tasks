use scripting additions

-- Conservative Phase 1 exporter.
-- Goal: run on macOS without AppleScript syntax errors and write a JSON file.
-- Usage:
--   osascript mac/export_completed_reminders_phase1.applescript /abs/path/to/output.json [/abs/path/to/local-map.json]
--
-- Behavior:
--   1) Export completed reminders from Apple Reminders.
--   2) Match reminder by list name + title against local sync map when available.
--   3) If local map is missing/unreadable, still write a valid JSON file with empty events.

on run argv
	if (count of argv) is 0 then error "Missing output json path"
	
	set outputPath to item 1 of argv
	if (count of argv) is 2 or (count of argv) is greater than 2 then
		set localMapPath to item 2 of argv
	else
		set localMapPath to my defaultLocalMapPath()
	end if
	
	set eventsJson to ""
	set eventCount to 0
	
	tell application "Reminders"
		repeat with oneList in every list
			set listName to (name of oneList) as text
			repeat with oneReminder in every reminder of oneList
				try
					if (completed of oneReminder) is true then
						set reminderTitle to (name of oneReminder) as text
						set completedAtText to my safeCompletedAt(oneReminder)
						set gtdId to my lookupGtdId(localMapPath, listName, reminderTitle)
						if gtdId is not "" then
							set oneEventJson to my buildEventJson(gtdId, listName, reminderTitle, completedAtText)
							if eventCount is greater than 0 then
								set eventsJson to eventsJson & "," & linefeed & oneEventJson
							else
								set eventsJson to oneEventJson
							end if
							set eventCount to eventCount + 1
						end if
					end if
				on error
					-- skip single reminder errors for robustness
				end try
			end repeat
		end repeat
	end tell
	
	my writeOutputJson(outputPath, localMapPath, eventsJson)
	return "OK exported=" & eventCount
end run

on defaultLocalMapPath()
	set scriptAlias to (path to me)
	set scriptPosixPath to POSIX path of scriptAlias
	set repoDir to do shell script "/usr/bin/dirname " & quoted form of scriptPosixPath & " | /usr/bin/xargs /usr/bin/dirname"
	return repoDir & "/sync/apple-reminders-local-map.json"
end defaultLocalMapPath

on lookupGtdId(localMapPath, listName, reminderTitle)
	try
		set escapedMapPath to quoted form of localMapPath
		set escapedListName to my shellQuoteText(listName)
		set escapedTitle to my shellQuoteText(reminderTitle)
		set py to "import json,sys\n" & ¬
			"from pathlib import Path\n" & ¬
			"p=Path(sys.argv[1])\n" & ¬
			"list_name=sys.argv[2]\n" & ¬
			"title=sys.argv[3]\n" & ¬
			"if not p.exists():\n" & ¬
			"    print('')\n" & ¬
			"    raise SystemExit(0)\n" & ¬
			"try:\n" & ¬
			"    data=json.loads(p.read_text(encoding='utf-8'))\n" & ¬
			"except Exception:\n" & ¬
			"    print('')\n" & ¬
			"    raise SystemExit(0)\n" & ¬
			"entries=data.get('entries',[]) if isinstance(data,dict) else []\n" & ¬
			"match_key=list_name+'\\n'+title\n" & ¬
			"for entry in entries:\n" & ¬
			"    if (entry.get('match_key') or '') == match_key:\n" & ¬
			"        print((entry.get('gtd_id') or '').strip())\n" & ¬
			"        raise SystemExit(0)\n" & ¬
			"print('')\n"
		set cmd to "/usr/bin/python3 -c " & quoted form of py & " " & escapedMapPath & " " & escapedListName & " " & escapedTitle
		set resultText to do shell script cmd
		if resultText is missing value then return ""
		return resultText as text
	on error
		return ""
	end try
end lookupGtdId

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
	set y to year of dateValue as integer
	set m to my monthNumber(month of dateValue)
	set d to day of dateValue as integer
	set hh to hours of dateValue as integer
	set mm to minutes of dateValue as integer
	set ss to seconds of dateValue as integer
	
	set yearText to my pad4(y)
	set monthText to my pad2(m)
	set dayText to my pad2(d)
	set hourText to my pad2(hh)
	set minuteText to my pad2(mm)
	set secondText to my pad2(ss)
	
	return yearText & "-" & monthText & "-" & dayText & "T" & hourText & ":" & minuteText & ":" & secondText
end isoFromDate

on monthNumber(monthValue)
	if monthValue is January then return 1
	if monthValue is February then return 2
	if monthValue is March then return 3
	if monthValue is April then return 4
	if monthValue is May then return 5
	if monthValue is June then return 6
	if monthValue is July then return 7
	if monthValue is August then return 8
	if monthValue is September then return 9
	if monthValue is October then return 10
	if monthValue is November then return 11
	if monthValue is December then return 12
	return 0
end monthNumber

on pad2(n)
	set s to (n as text)
	if (length of s) is 1 then return "0" & s
	return s
end pad2

on pad4(n)
	set s to (n as text)
	repeat while (length of s) is less than 4
		set s to "0" & s
	end repeat
	return s
end pad4

on buildEventJson(gtdId, listName, reminderTitle, completedAtText)
	set eventId to gtdId & "::" & listName & "::" & reminderTitle & "::" & completedAtText
	set jsonText to "  {" & linefeed & ¬
		"    \"event_id\": \"" & my jsonEscape(eventId) & "\"," & linefeed & ¬
		"    \"event_type\": \"completed\"," & linefeed & ¬
		"    \"source\": \"apple_reminders_phase1_local_map\"," & linefeed & ¬
		"    \"gtd_id\": \"" & my jsonEscape(gtdId) & "\"," & linefeed & ¬
		"    \"completed_at\": \"" & my jsonEscape(completedAtText) & "\"," & linefeed & ¬
		"    \"apple_list_name\": \"" & my jsonEscape(listName) & "\"," & linefeed & ¬
		"    \"title\": \"" & my jsonEscape(reminderTitle) & "\"," & linefeed & ¬
		"    \"match_key\": \"" & my jsonEscape(listName & linefeed & reminderTitle) & "\"" & linefeed & ¬
		"  }"
	return jsonText
end buildEventJson

on writeOutputJson(outputPath, localMapPath, eventsJson)
	set headerText to "{" & linefeed & ¬
		"  \"version\": \"0.4.0-phase1-local-map-safe\"," & linefeed & ¬
		"  \"generated_at\": null," & linefeed & ¬
		"  \"local_map_path\": \"" & my jsonEscape(localMapPath) & "\"," & linefeed & ¬
		"  \"events\": ["
	set footerText to linefeed & "  ]" & linefeed & "}" & linefeed
	set finalJson to headerText & linefeed & eventsJson & footerText
	my writeTextFile(outputPath, finalJson)
end writeOutputJson

on writeTextFile(outputPath, contentText)
	set fileRef to open for access POSIX file outputPath with write permission
	try
		set eof of fileRef to 0
		write contentText to fileRef as «class utf8»
		close access fileRef
	on error errMsg number errNum
		try
			close access fileRef
		end try
		error errMsg number errNum
	end try
end writeTextFile

on jsonEscape(inputText)
	set t to inputText as text
	set t to my replaceText("\\", "\\\\", t)
	set t to my replaceText("\"", "\\\"", t)
	set t to my replaceText(return, "\\n", t)
	set t to my replaceText(linefeed, "\\n", t)
	set t to my replaceText(tab, "\\t", t)
	return t
end jsonEscape

on replaceText(findText, replaceWithText, sourceText)
	set oldDelims to AppleScript's text item delimiters
	set AppleScript's text item delimiters to findText
	set textItems to every text item of sourceText
	set AppleScript's text item delimiters to replaceWithText
	set newText to textItems as text
	set AppleScript's text item delimiters to oldDelims
	return newText
end replaceText

on shellQuoteText(inputText)
	return quoted form of (inputText as text)
end shellQuoteText