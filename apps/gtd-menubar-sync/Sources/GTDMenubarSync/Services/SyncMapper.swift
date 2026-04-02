import Foundation

struct ReminderPayload {
    let taskID: String
    let title: String
    let note: String
    let listName: String
    let dueDate: String?
}

struct SyncMapper {
    private let shanghaiTZ = TimeZone(identifier: "Asia/Shanghai") ?? .current

    private let bucketToList: [String: String] = [
        "today": "下一步行动@NextAction",
        "tomorrow": "下一步行动@NextAction",
        "future": "可能的事@Maybe",
        "archive": "可能的事@Maybe"
    ]

    private let categoryToList: [String: String] = [
        "inbox": "收集箱@Inbox",
        "project": "项目@Project",
        "next_action": "下一步行动@NextAction",
        "waiting_for": "等待@Waiting For",
        "maybe": "可能的事@Maybe"
    ]

    func payload(for task: GTDTask) -> ReminderPayload {
        let tags = normalizeTags(task.tags ?? [])
        let title = renderTitle(task.title, tags: tags)
        let note = task.note ?? ""
        let listName = categoryToList[task.category ?? ""] ?? bucketToList[task.bucket ?? "today"] ?? "下一步行动@NextAction"
        return ReminderPayload(
            taskID: task.id,
            title: title,
            note: note,
            listName: listName,
            dueDate: resolveDueDate(task)
        )
    }

    private func normalizeTags(_ tags: [String]) -> [String] {
        var result: [String] = []
        var seen: Set<String> = []
        for tag in tags {
            let pretty = "#" + tag.replacingOccurrences(of: "#", with: "").uppercased()
            if !pretty.isEmpty, !seen.contains(pretty) {
                seen.insert(pretty)
                result.append(pretty)
            }
        }
        return result
    }

    private func renderTitle(_ title: String, tags: [String]) -> String {
        guard !tags.isEmpty else { return title }
        return title + " " + tags.joined(separator: " ")
    }

    private func resolveDueDate(_ task: GTDTask) -> String? {
        if let dueDate = task.dueDate, !dueDate.isEmpty { return dueDate }
        return bucketDueDate(task.bucket)
    }

    private func bucketDueDate(_ bucket: String?) -> String? {
        let calendar = Calendar(identifier: .gregorian)
        let now = Date()
        switch bucket {
        case "today":
            return isoDate(now, calendar: calendar)
        case "tomorrow":
            guard let next = calendar.date(byAdding: .day, value: 1, to: now) else { return nil }
            return isoDate(next, calendar: calendar)
        default:
            return nil
        }
    }

    private func isoDate(_ date: Date, calendar: Calendar) -> String {
        var cal = calendar
        cal.timeZone = shanghaiTZ
        let comps = cal.dateComponents([.year, .month, .day], from: date)
        return String(format: "%04d-%02d-%02d", comps.year ?? 0, comps.month ?? 0, comps.day ?? 0)
    }
}
