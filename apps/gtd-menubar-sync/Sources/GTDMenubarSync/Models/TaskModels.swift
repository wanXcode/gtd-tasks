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

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case status
        case bucket
        case quadrant
        case tags
        case note
        case dueDate = "due_date"
        case category
        case updatedAt = "updated_at"
    }
}

struct GTDChange: Codable, Identifiable {
    let changeID: Int
    let taskID: String?
    let action: String
    let task: GTDTask?

    var id: Int { changeID }

    enum CodingKeys: String, CodingKey {
        case changeID = "change_id"
        case taskID = "task_id"
        case action
        case task
    }
}

struct GTDChangesResponse: Codable {
    let items: [GTDChange]
    let nextChangeID: Int

    enum CodingKeys: String, CodingKey {
        case items
        case nextChangeID = "next_change_id"
    }
}

struct GTDTasksResponse: Codable {
    let items: [GTDTask]
}

struct AppleMappingItem: Codable {
    let taskID: String
    let appleReminderID: String

    enum CodingKeys: String, CodingKey {
        case taskID = "task_id"
        case appleReminderID = "apple_reminder_id"
    }
}

struct AppleMappingsResponse: Codable {
    let items: [AppleMappingItem]
}

struct ReminderMapping: Codable {
    let taskID: String
    let reminderID: String
}

struct SyncClientState: Codable {
    let clientID: String
    let lastChangeID: Int
    let lastSyncAt: Date?

    enum CodingKeys: String, CodingKey {
        case clientID = "client_id"
        case lastChangeID = "last_change_id"
        case lastSyncAt = "last_sync_at"
    }
}
