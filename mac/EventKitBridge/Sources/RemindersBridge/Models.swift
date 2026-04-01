import Foundation

struct BridgeSuccess: Encodable {
    let success: Bool = true
    let action: String
    let reminder_id: String?
    let calendars: [CalendarInfo]?
    let permission: String?
    let message: String?
    let preflight: PreflightInfo?
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

struct PreflightInfo: Encodable {
    let permission: String
    let calendar_count: Int
    let default_calendar_id: String?
    let default_calendar_title: String?
    let requested_list_name: String?
    let requested_calendar_id: String?
    let requested_calendar_found: Bool
}

struct ReminderPayload: Decodable {
    let reminder_id: String?
    let title: String?
    let list_name: String?
    let calendar_id: String?
    let note: String?
    let completed: Bool?
    let due_date: String?
}
