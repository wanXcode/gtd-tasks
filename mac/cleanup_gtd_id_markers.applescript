use scripting additions

-- 批量清理 Apple Reminders 备注中的 [GTD_ID] 标记
-- 用法：osascript mac/cleanup_gtd_id_markers.applescript

on run
	set targetLists to {"收集箱@Inbox", "下一步行动@NextAction", "项目@Project", "等待@Waiting For", "可能的事@Maybe"}
	set cleanedCount to 0
	
	tell application "Reminders"
		repeat with listName in targetLists
			try
				set targetList to list listName
				repeat with r in reminders of targetList
					set oldBody to my safeReminderBody(r)
					set newBody to my stripGtdMarker(oldBody)
					if newBody is not oldBody then
						set body of r to newBody
						set cleanedCount to cleanedCount + 1
					end if
				end repeat
			on error
				-- 列表不存在则跳过
			end try
		end repeat
	end tell
	
	return "OK cleaned=" & cleanedCount
end run

on safeReminderBody(oneReminder)
	try
		return body of oneReminder as text
	on error
		try
			return body of contents of oneReminder as text
		on error
			return ""
		end try
	end try
end safeReminderBody

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
