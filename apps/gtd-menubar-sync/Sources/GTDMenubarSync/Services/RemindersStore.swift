import EventKit
import Foundation

enum RemindersStoreError: LocalizedError {
    case permissionNotGranted
    case calendarUnavailable(String)
    case reminderNotFound(String)

    var errorDescription: String? {
        switch self {
        case .permissionNotGranted:
            return "Reminders 权限未授权"
        case .calendarUnavailable(let name):
            return "找不到目标日历：\(name)"
        case .reminderNotFound(let id):
            return "找不到 reminder：\(id)"
        }
    }
}

actor RemindersStore {
    private let permissionManager: PermissionManager
    private let store = EKEventStore()

    init(permissionManager: PermissionManager) {
        self.permissionManager = permissionManager
    }

    func preflight() async -> ReminderPermissionStatus {
        await permissionManager.currentStatus()
    }

    func listCalendars() async throws -> [String] {
        let status = await permissionManager.currentStatus()
        guard status == .authorized else { throw RemindersStoreError.permissionNotGranted }
        refreshIfNeeded()
        return store.calendars(for: .reminder).map(\.title)
    }

    func createReminder(_ payload: ReminderPayload) async throws -> String {
        let status = await permissionManager.currentStatus()
        guard status == .authorized else { throw RemindersStoreError.permissionNotGranted }

        let reminder = EKReminder(eventStore: store)
        reminder.title = payload.title
        reminder.notes = payload.note
        reminder.dueDateComponents = parseDueDate(payload.dueDate)
        reminder.calendar = try resolveCalendar(named: payload.listName)
        try store.save(reminder, commit: true)
        return reminder.calendarItemIdentifier
    }

    func updateReminder(reminderID: String, payload: ReminderPayload) async throws {
        let reminder = try fetchReminder(reminderID)
        reminder.title = payload.title
        reminder.notes = payload.note
        reminder.dueDateComponents = parseDueDate(payload.dueDate)
        try store.save(reminder, commit: true)
    }

    func moveReminder(reminderID: String, to listName: String) async throws {
        let reminder = try fetchReminder(reminderID)
        reminder.calendar = try resolveCalendar(named: listName)
        try store.save(reminder, commit: true)
    }

    func completeReminder(reminderID: String, completed: Bool = true) async throws {
        let reminder = try fetchReminder(reminderID)
        reminder.isCompleted = completed
        reminder.completionDate = completed ? Date() : nil
        try store.save(reminder, commit: true)
    }

    func deleteReminder(reminderID: String) async throws {
        let reminder = try fetchReminder(reminderID)
        try store.remove(reminder, commit: true)
    }

    private func fetchReminder(_ id: String) throws -> EKReminder {
        refreshIfNeeded()
        guard let reminder = store.calendarItem(withIdentifier: id) as? EKReminder else {
            throw RemindersStoreError.reminderNotFound(id)
        }
        return reminder
    }

    private func resolveCalendar(named title: String) throws -> EKCalendar {
        refreshIfNeeded()
        let wanted = normalize(title)
        let calendars = store.calendars(for: .reminder)
        if let exact = calendars.first(where: { normalize($0.title) == wanted }) {
            return exact
        }
        refreshIfNeeded(force: true)
        let refreshed = store.calendars(for: .reminder)
        if let exact = refreshed.first(where: { normalize($0.title) == wanted }) {
            return exact
        }
        throw RemindersStoreError.calendarUnavailable(title)
    }

    private func normalize(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "\u{00A0}", with: " ")
    }

    private func refreshIfNeeded(force: Bool = false) {
        if force {
            _ = store.refreshSourcesIfNecessary()
            return
        }
        if store.calendars(for: .reminder).isEmpty {
            _ = store.refreshSourcesIfNecessary()
        }
    }

    private func parseDueDate(_ raw: String?) -> DateComponents? {
        guard let raw, !raw.isEmpty else { return nil }
        let parts = raw.split(separator: "-").compactMap { Int($0) }
        guard parts.count == 3 else { return nil }
        var comps = DateComponents()
        comps.calendar = Calendar(identifier: .gregorian)
        comps.timeZone = TimeZone(identifier: "Asia/Shanghai") ?? .current
        comps.year = parts[0]
        comps.month = parts[1]
        comps.day = parts[2]
        return comps
    }
}
