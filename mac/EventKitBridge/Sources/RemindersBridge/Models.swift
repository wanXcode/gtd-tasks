import Foundation

struct BridgeSuccess: Encodable {
    let success: Bool = true
    let action: String
    let reminder_id: String?
    let calendars: [CalendarInfo]?
    let permission: String?
    let message: String?
}

struct BridgeError: Encodable, Error {
    let success: Bool = false
    let action: String
    let error_code: String
    let error_message: String
}

struct CalendarInfo: Encodable {
    let id: String
    let title: String
}

struct ReminderPayload: Decodable {
    let reminder_id: String?
    let title: String?
    let list_name: String?
    let note: String?
    let completed: Bool?
}
