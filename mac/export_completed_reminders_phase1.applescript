use scripting additions

on run argv
    if (count of argv) is less than 1 then error "Missing output json path"

    set outputPath to item 1 of argv
    set generatedAt to do shell script "date -u +%Y-%m-%dT%H:%M:%SZ"
    set jsonText to "{\"version\":\"0.4.0-phase1\",\"generated_at\":\"" & generatedAt & "\",\"events\":["
    set firstItem to true

    tell application "Reminders"
        repeat with oneList in every list
            set listName to name of oneList as text
            repeat with oneReminder in every reminder of oneList
                try
                    if completed of oneReminder is true then
                        set reminderTitle to name of oneReminder as text
                        set reminderBody to ""
                        try
                            set reminderBody to body of oneReminder as text
                        end try
                        set completedAt to my safeCompletionDate(oneReminder)
                        set gtdId to my extractGtdId(reminderBody)
                        set eventId to my buildEventId(gtdId, completedAt, reminderTitle)
                        set itemJson to my eventJson(eventId, gtdId, listName, reminderTitle, completedAt)
                        if firstItem then
                            set jsonText to jsonText & itemJson
                            set firstItem to false
                        else
                            set jsonText to jsonText & "," & itemJson
                        end if
                    end if
                on error
                end try
            end repeat
        end repeat
    end tell

    set jsonText to jsonText & "]}"
    my writeText(outputPath, jsonText)
    return outputPath
end run

on eventJson(eventId, gtdId, listName, reminderTitle, completedAt)
    return "{\"event_id\":\"" & my jsonEscape(eventId) & "\",\"event_type\":\"completed\",\"gtd_id\":\"" & my jsonEscape(gtdId) & "\",\"list_name\":\"" & my jsonEscape(listName) & "\",\"title\":\"" & my jsonEscape(reminderTitle) & "\",\"completed_at\":\"" & my jsonEscape(completedAt) & "\",\"source\":\"apple_reminders_phase1\"}"
end eventJson

on safeCompletionDate(oneReminder)
    try
        set completedDate to completion date of oneReminder
        if completedDate is missing value then error "missing completion date"
        return (completedDate as text)
    on error
        return do shell script "date -u +%Y-%m-%dT%H:%M:%SZ"
    end try
end safeCompletionDate

on extractGtdId(reminderBody)
    set marker to "[GTD_ID]"
    set tid to ""
    try
        set oldDelims to AppleScript's text item delimiters
        set AppleScript's text item delimiters to marker
        set parts to text items of reminderBody
        set AppleScript's text item delimiters to oldDelims
        if (count of parts) > 1 then
            set tailText to item 2 of parts
            set tid to my firstToken(tailText)
        end if
    on error
        set AppleScript's text item delimiters to oldDelims
    end try
    return tid
end extractGtdId

on firstToken(inputText)
    set cleanText to my replaceText(return, " ", inputText)
    set cleanText to my replaceText(linefeed, " ", cleanText)
    set cleanText to my replaceText(tab, " ", cleanText)
    set oldDelims to AppleScript's text item delimiters
    set AppleScript's text item delimiters to " "
    set parts to text items of cleanText
    set AppleScript's text item delimiters to oldDelims
    repeat with onePart in parts
        set v to (onePart as text)
        if v is not "" then return v
    end repeat
    return ""
end firstToken

on buildEventId(gtdId, completedAt, reminderTitle)
    if gtdId is not "" then
        return gtdId & "::" & completedAt
    end if
    return my jsonEscape(reminderTitle) & "::" & completedAt
end buildEventId

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

on writeText(outputPath, contentText)
    set shellText to "/bin/mkdir -p $(/usr/bin/dirname " & quoted form of outputPath & ") ; /usr/bin/printf %s " & quoted form of contentText & " > " & quoted form of outputPath
    do shell script shellText
end writeText
