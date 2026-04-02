import EventKit
import Foundation

actor PermissionManager {
    private let eventStore = EKEventStore()

    func currentStatus() -> ReminderPermissionStatus {
        map(EKEventStore.authorizationStatus(for: .reminder))
    }

    func requestAccessIfNeeded() async -> ReminderPermissionStatus {
        let current = currentStatus()
        guard current == .notDetermined || current == .unknown else { return current }

        if #available(macOS 14.0, *) {
            do {
                _ = try await eventStore.requestFullAccessToReminders()
            } catch {
                return currentStatus()
            }
        } else {
            do {
                _ = try await withCheckedThrowingContinuation { continuation in
                    eventStore.requestAccess(to: .reminder) { granted, error in
                        if let error {
                            continuation.resume(throwing: error)
                        } else {
                            continuation.resume(returning: granted)
                        }
                    }
                } as Bool
            } catch {
                return currentStatus()
            }
        }

        return currentStatus()
    }

    private func map(_ status: EKAuthorizationStatus) -> ReminderPermissionStatus {
        switch status {
        case .authorized, .fullAccess:
            return .authorized
        case .denied:
            return .denied
        case .restricted:
            return .restricted
        case .notDetermined:
            return .notDetermined
        case .writeOnly:
            return .authorized
        @unknown default:
            return .unknown
        }
    }
}
