import Foundation

struct GTDTask: Codable, Identifiable {
    let id: String
    let title: String
    let status: String
    let bucket: String?
    let quadrant: String?
    let tags: [String]?
    let note: String?
    let dueDate: String?
    let category: String?
    let updatedAt: String?
}

struct GTDChange: Codable, Identifiable {
    let changeID: Int
    let taskID: String?
    let action: String
    let task: GTDTask?

    var id: Int { changeID }
}

struct GTDChangesResponse: Codable {
    let items: [GTDChange]
    let nextChangeID: Int
}

struct ReminderMapping: Codable {
    let taskID: String
    let reminderID: String
}
