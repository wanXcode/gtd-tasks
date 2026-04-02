import Foundation
import EventKit

final class EventKitService {
    private let store = EKEventStore()

    private func parseDueDateComponents(_ raw: String?) -> DateComponents? {
        guard let raw, !raw.isEmpty else { return nil }
        let parts = raw.split(separator: "-").map(String.init)
        guard parts.count == 3,
              let year = Int(parts[0]),
              let month = Int(parts[1]),
              let day = Int(parts[2]) else {
            return nil
        }
        var comps = DateComponents()
        comps.calendar = Calendar(identifier: .gregorian)
        comps.timeZone = TimeZone.current
        comps.year = year
        comps.month = month
        comps.day = day
        return comps
    }

    private func currentPermission() -> String {
        let status = EKEventStore.authorizationStatus(for: .reminder)
        switch status {
        case .authorized, .fullAccess:
            return "authorized"
        case .denied:
            return "denied"
        case .restricted:
            return "restricted"
        case .notDetermined:
            return "not_determined"
        case .writeOnly:
            return "write_only"
        @unknown default:
            return "unknown"
        }
    }

    private func resolveCalendar(listName: String?, calendarId: String?) -> EKCalendar? {
        if let calendarId, !calendarId.isEmpty {
            if let byId = store.calendars(for: .reminder).first(where: { $0.calendarIdentifier == calendarId }) {
                return byId
            }
        }
        if let listName, !listName.isEmpty {
            return findCalendar(named: listName)
        }
        return nil
    }

    func checkPermission() -> BridgeSuccess {
        let permission = currentPermission()
        return BridgeSuccess(action: "check-permission", reminder_id: nil, calendars: nil, permission: permission, message: nil, preflight: nil)
    }

    func requestPermission() -> BridgeSuccess {
        let semaphore = DispatchSemaphore(value: 0)
        var permission = currentPermission()
        if permission == "authorized" {
            return BridgeSuccess(action: "request-permission", reminder_id: nil, calendars: nil, permission: permission, message: "already_authorized", preflight: nil)
        }

        if #available(macOS 14.0, *) {
            store.requestFullAccessToReminders { granted, _ in
                permission = granted ? "authorized" : self.currentPermission()
                semaphore.signal()
            }
        } else {
            store.requestAccess(to: .reminder) { granted, _ in
                permission = granted ? "authorized" : self.currentPermission()
                semaphore.signal()
            }
        }

        _ = semaphore.wait(timeout: .now() + 15)
        permission = currentPermission()
        let message = permission == "authorized" ? "granted" : "not_granted"
        return BridgeSuccess(action: "request-permission", reminder_id: nil, calendars: nil, permission: permission, message: message, preflight: nil)
    }

    func preflight(_ payload: ReminderPayload?) -> BridgeSuccess {
        let calendars = store.calendars(for: .reminder)
        let requested = resolveCalendar(listName: payload?.list_name, calendarId: payload?.calendar_id)
        let `default` = store.defaultCalendarForNewReminders()
        let info = PreflightInfo(
            permission: currentPermission(),
            calendar_count: calendars.count,
            default_calendar_id: `default`?.calendarIdentifier,
            default_calendar_title: `default`?.title,
            requested_list_name: payload?.list_name,
            requested_calendar_id: requested?.calendarIdentifier ?? payload?.calendar_id,
            requested_calendar_found: requested != nil
        )
        return BridgeSuccess(action: "preflight", reminder_id: nil, calendars: nil, permission: info.permission, message: nil, preflight: info)
    }

    func listCalendars() -> BridgeSuccess {
        let calendars = store.calendars(for: .reminder).map { CalendarInfo(id: $0.calendarIdentifier, title: $0.title) }
        return BridgeSuccess(action: "list-calendars", reminder_id: nil, calendars: calendars, permission: nil, message: nil, preflight: nil)
    }

    func get(_ payload: ReminderPayload?) -> Result<BridgeSuccess, BridgeError> {
        guard let reminderId = payload?.reminder_id, !reminderId.isEmpty else {
            return .failure(BridgeError(action: "get", error_code: "MISSING_REMINDER_ID", error_message: "reminder_id is required"))
        }
        guard let reminder = store.calendarItem(withIdentifier: reminderId) as? EKReminder else {
            return .failure(BridgeError(action: "get", error_code: "REMINDER_NOT_FOUND", error_message: "reminder not found"))
        }
        let completed = reminder.isCompleted ? "completed" : "active"
        return .success(BridgeSuccess(action: "get", reminder_id: reminder.calendarItemIdentifier, calendars: nil, permission: nil, message: completed, preflight: nil))
    }

    func create(_ payload: ReminderPayload?) -> Result<BridgeSuccess, BridgeError> {
        guard let payload, let title = payload.title, !title.isEmpty else {
            return .failure(BridgeError(action: "create", error_code: "MISSING_TITLE", error_message: "title is required"))
        }
        do {
            let reminder = EKReminder(eventStore: store)
            reminder.title = title
            reminder.notes = payload.note
            reminder.dueDateComponents = parseDueDateComponents(payload.due_date)
            if let calendar = resolveCalendar(listName: payload.list_name, calendarId: payload.calendar_id) {
                reminder.calendar = calendar
            } else if reminder.calendar == nil, let `default` = store.defaultCalendarForNewReminders() {
                reminder.calendar = `default`
            }
            if reminder.calendar == nil {
                return .failure(BridgeError(action: "create", error_code: "CALENDAR_UNAVAILABLE", error_message: "target/default calendar unavailable"))
            }
            try store.save(reminder, commit: true)
            return .success(BridgeSuccess(action: "create", reminder_id: reminder.calendarItemIdentifier, calendars: nil, permission: nil, message: nil, preflight: nil))
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
            reminder.dueDateComponents = parseDueDateComponents(payload?.due_date)
            try store.save(reminder, commit: true)
            return .success(BridgeSuccess(action: "update", reminder_id: reminder.calendarItemIdentifier, calendars: nil, permission: nil, message: nil, preflight: nil))
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
        guard let calendar = resolveCalendar(listName: listName, calendarId: payload?.calendar_id) else {
            return .failure(BridgeError(action: "move", error_code: "LIST_NOT_FOUND", error_message: "target list not found"))
        }
        do {
            reminder.calendar = calendar
            try store.save(reminder, commit: true)
            return .success(BridgeSuccess(action: "move", reminder_id: reminder.calendarItemIdentifier, calendars: nil, permission: nil, message: nil, preflight: nil))
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
            return .success(BridgeSuccess(action: "complete", reminder_id: reminder.calendarItemIdentifier, calendars: nil, permission: nil, message: nil, preflight: nil))
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
            return .success(BridgeSuccess(action: "delete", reminder_id: reminderId, calendars: nil, permission: nil, message: nil, preflight: nil))
        } catch {
            return .failure(BridgeError(action: "delete", error_code: "DELETE_FAILED", error_message: error.localizedDescription))
        }
    }

    private func findCalendar(named title: String) -> EKCalendar? {
        store.calendars(for: .reminder).first(where: { $0.title == title })
    }
}
