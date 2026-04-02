import EventKit
import Foundation

struct RemindersStore {
    let permissionManager: PermissionManager

    func preflight() async -> ReminderPermissionStatus {
        await permissionManager.currentStatus()
    }

    // 占位：后续补 reminders CRUD
    func listCalendars() async throws -> [String] {
        let status = await permissionManager.currentStatus()
        guard status == .authorized else { return [] }
        let store = EKEventStore()
        return store.calendars(for: .reminder).map(\.title)
    }
}
