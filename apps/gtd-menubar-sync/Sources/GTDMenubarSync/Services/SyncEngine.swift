import Foundation

struct SyncEngine {
    let permissionManager: PermissionManager
    let serverAPI: ServerAPI
    let remindersStore: RemindersStore
    let localStore: LocalStore
    let logger: AppLogger

    func runOnce() async -> SyncResultSnapshot {
        let permission = await permissionManager.currentStatus()
        guard permission == .authorized else {
            logger.error("sync skipped: reminders permission not authorized")
            return SyncResultSnapshot(
                status: .permissionRequired,
                permissionStatus: permission,
                serverStatus: .unknown,
                lastSuccessAt: nil,
                lastErrorSummary: "Reminders 权限未授权"
            )
        }

        let serverHealth = await serverAPI.healthcheck()
        guard serverHealth == .online else {
            logger.error("sync skipped: server offline or degraded")
            return SyncResultSnapshot(
                status: .serverError,
                permissionStatus: permission,
                serverStatus: serverHealth,
                lastSuccessAt: nil,
                lastErrorSummary: "服务端不可用"
            )
        }

        do {
            let calendars = try await remindersStore.listCalendars()
            logger.info("sync preflight ok, calendars=\(calendars.count)")
            return SyncResultSnapshot(
                status: .healthy,
                permissionStatus: permission,
                serverStatus: serverHealth,
                lastSuccessAt: Date(),
                lastErrorSummary: nil
            )
        } catch {
            logger.error("sync failed: \(error.localizedDescription)")
            return SyncResultSnapshot(
                status: .failed,
                permissionStatus: permission,
                serverStatus: serverHealth,
                lastSuccessAt: nil,
                lastErrorSummary: error.localizedDescription
            )
        }
    }
}
