use scripting additions

on run argv
    if (count of argv) is less than 1 then error "Missing output json path"

    set outputPath to item 1 of argv
    set jsonText to "{\"version\":\"phase1-minimal\",\"events\":["
    set firstItem to true

    tell application "Reminders"
        repeat with oneList in every list
            set listName to name of oneList as text
            repeat with oneReminder in every reminder of oneList
                try
                    if completed of oneReminder is true then
                        set reminderTitle to name of oneReminder as text
                        set itemJson to my eventJson(listName, reminderTitle)
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

on eventJson(listName, reminderTitle)
    return "{\"list_name\":\"" & my jsonEscape(listName) & "\",\"title\":\"" & my jsonEscape(reminderTitle) & "\"}"
end eventJson

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
