import Foundation
import EventKit

final class EventKitService {
    private let store = EKEventStore()

    func checkPermission() -> BridgeSuccess {
        let status = EKEventStore.authorizationStatus(for: .reminder)
        let permission: String
        switch status {
        case .authorized, .fullAccess:
            permission = "authorized"
        case .denied:
            permission = "denied"
        case .restricted:
            permission = "restricted"
        case .notDetermined:
            permission = "not_determined"
        case .writeOnly:
            permission = "write_only"
        @unknown default:
            permission = "unknown"
        }
        return BridgeSuccess(action: "check-permission", reminder_id: nil, calendars: nil, permission: permission, message: nil)
    }

    func listCalendars() -> BridgeSuccess {
        let calendars = store.calendars(for: .reminder).map { CalendarInfo(id: $0.calendarIdentifier, title: $0.title) }
        return BridgeSuccess(action: "list-calendars", reminder_id: nil, calendars: calendars, permission: nil, message: nil)
    }

    func create(_ payload: ReminderPayload?) -> Result<BridgeSuccess, BridgeError> {
        guard let payload, let title = payload.title, !title.isEmpty else {
            return .failure(BridgeError(action: "create", error_code: "MISSING_TITLE", error_message: "title is required"))
        }
        do {
            let reminder = EKReminder(eventStore: store)
            reminder.title = title
            reminder.notes = payload.note
            if let listName = payload.list_name, let calendar = findCalendar(named: listName) {
                reminder.calendar = calendar
            } else if reminder.calendar == nil, let `default` = store.defaultCalendarForNewReminders() {
                reminder.calendar = `default`
            }
            try store.save(reminder, commit: true)
            return .success(BridgeSuccess(action: "create", reminder_id: reminder.calendarItemIdentifier, calendars: nil, permission: nil, message: nil))
        } catch {
            return .failure(BridgeError(action: "create", error_code: "CREATE_FAILED", error_message: error.localizedDescription))
        }
    }

    func update(_ payload: ReminderPayload?) -> Result<BridgeSuccess, BridgeError> {
        guard let reminderId = payload?.reminder_id, !reminderId.isEmpty else {
            return .failure(BridgeError(action: "update", error_code: "MISSING_REMINDER_ID", error_message: "reminder_id is required"))
        }
        guard let reminder = store.calendarItem(withIdentifier: reminderId) as? EKReminder else {
            return .failure(BridgeError(action: "update", error_code: "REMINDER_NOT_FOUND", error_message: "reminder not found"))
        }
        do {
            if let title = payload?.title, !title.isEmpty {
                reminder.title = title
            }
            reminder.notes = payload?.note
            try store.save(reminder, commit: true)
            return .success(BridgeSuccess(action: "update", reminder_id: reminder.calendarItemIdentifier, calendars: nil, permission: nil, message: nil))
        } catch {
            return .failure(BridgeError(action: "update", error_code: "UPDATE_FAILED", error_message: error.localizedDescription))
        }
    }

    func move(_ payload: ReminderPayload?) -> Result<BridgeSuccess, BridgeError> {
        guard let reminderId = payload?.reminder_id, !reminderId.isEmpty else {
            return .failure(BridgeError(action: "move", error_code: "MISSING_REMINDER_ID", error_message: "reminder_id is required"))
        }
        guard let listName = payload?.list_name, !listName.isEmpty else {
            return .failure(BridgeError(action: "move", error_code: "MISSING_LIST_NAME", error_message: "list_name is required"))
        }
        guard let reminder = store.calendarItem(withIdentifier: reminderId) as? EKReminder else {
            return .failure(BridgeError(action: "move", error_code: "REMINDER_NOT_FOUND", error_message: "reminder not found"))
        }
        guard let calendar = findCalendar(named: listName) else {
            return .failure(BridgeError(action: "move", error_code: "LIST_NOT_FOUND", error_message: "target list not found"))
        }
        do {
            reminder.calendar = calendar
            try store.save(reminder, commit: true)
            return .success(BridgeSuccess(action: "move", reminder_id: reminder.calendarItemIdentifier, calendars: nil, permission: nil, message: nil))
        } catch {
            return .failure(BridgeError(action: "move", error_code: "MOVE_FAILED", error_message: error.localizedDescription))
        }
    }

    func complete(_ payload: ReminderPayload?) -> Result<BridgeSuccess, BridgeError> {
        guard let reminderId = payload?.reminder_id, !reminderId.isEmpty else {
            return .failure(BridgeError(action: "complete", error_code: "MISSING_REMINDER_ID", error_message: "reminder_id is required"))
        }
        guard let reminder = store.calendarItem(withIdentifier: reminderId) as? EKReminder else {
            return .failure(BridgeError(action: "complete", error_code: "REMINDER_NOT_FOUND", error_message: "reminder not found"))
        }
        do {
            reminder.isCompleted = payload?.completed ?? true
            if reminder.isCompleted {
                reminder.completionDate = Date()
            } else {
                reminder.completionDate = nil
            }
            try store.save(reminder, commit: true)
            return .success(BridgeSuccess(action: "complete", reminder_id: reminder.calendarItemIdentifier, calendars: nil, permission: nil, message: nil))
        } catch {
            return .failure(BridgeError(action: "complete", error_code: "COMPLETE_FAILED", error_message: error.localizedDescription))
        }
    }

    func delete(_ payload: ReminderPayload?) -> Result<BridgeSuccess, BridgeError> {
        guard let reminderId = payload?.reminder_id, !reminderId.isEmpty else {
            return .failure(BridgeError(action: "delete", error_code: "MISSING_REMINDER_ID", error_message: "reminder_id is required"))
        }
        guard let reminder = store.calendarItem(withIdentifier: reminderId) as? EKReminder else {
            return .failure(BridgeError(action: "delete", error_code: "REMINDER_NOT_FOUND", error_message: "reminder not found"))
        }
        do {
            try store.remove(reminder, commit: true)
            return .success(BridgeSuccess(action: "delete", reminder_id: reminderId, calendars: nil, permission: nil, message: nil))
        } catch {
            return .failure(BridgeError(action: "delete", error_code: "DELETE_FAILED", error_message: error.localizedDescription))
        }
    }

    private func findCalendar(named title: String) -> EKCalendar? {
        store.calendars(for: .reminder).first(where: { $0.title == title })
    }
}
