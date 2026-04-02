import Foundation

struct SyncEngine {
    let permissionManager: PermissionManager
    let serverAPI: ServerAPI
    let remindersStore: RemindersStore
    let localStore: LocalStore
    let logger: AppLogger
    let mapper = SyncMapper()

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
            _ = try await remindersStore.listCalendars()

            let clientState = localStore.loadClientState() ?? SyncClientState(
                clientID: "mac-menubar-primary",
                lastChangeID: 0,
                lastSyncAt: nil
            )
            let serverMappings = try await serverAPI.fetchMappings()
            var localMappings = localStore.loadMappings()
            for item in serverMappings.items where localMappings[item.taskID] == nil {
                localMappings[item.taskID] = item.appleReminderID
            }

            let changesResponse = try await serverAPI.fetchChanges(since: clientState.lastChangeID, limit: 100)
            var ackUpto = clientState.lastChangeID
            var remoteMappingsToSave: [AppleMappingItem] = []
            var firstError: String?

            for change in changesResponse.items {
                guard let task = change.task else {
                    continue
                }

                let payload = mapper.payload(for: task)
                do {
                    switch change.action {
                    case "create", "update":
                        if let reminderID = localMappings[task.id] {
                            try await remindersStore.updateReminder(reminderID: reminderID, payload: payload)
                            try await remindersStore.moveReminder(reminderID: reminderID, to: payload.listName)
                        } else {
                            let reminderID = try await remindersStore.createReminder(payload)
                            localMappings[task.id] = reminderID
                            remoteMappingsToSave.append(.init(taskID: task.id, appleReminderID: reminderID))
                        }
                    case "done":
                        if let reminderID = localMappings[task.id] {
                            try await remindersStore.completeReminder(reminderID: reminderID)
                        }
                    case "delete":
                        if let reminderID = localMappings[task.id] {
                            try await remindersStore.deleteReminder(reminderID: reminderID)
                            localMappings.removeValue(forKey: task.id)
                        }
                    default:
                        break
                    }

                    ackUpto = max(ackUpto, change.changeID)
                } catch {
                    firstError = error.localizedDescription
                    logger.error("sync change failed: task=\(task.id) action=\(change.action) error=\(error.localizedDescription)")
                    break
                }
            }

            localStore.saveMappings(localMappings)
            if !remoteMappingsToSave.isEmpty {
                try await serverAPI.saveMappings(remoteMappingsToSave)
            }
            if ackUpto > clientState.lastChangeID {
                try await serverAPI.ackChanges(clientID: clientState.clientID, lastChangeID: ackUpto)
            }

            let successDate = Date()
            localStore.saveClientState(
                SyncClientState(
                    clientID: clientState.clientID,
                    lastChangeID: ackUpto,
                    lastSyncAt: successDate
                )
            )

            return SyncResultSnapshot(
                status: firstError == nil ? .healthy : .partialFailure,
                permissionStatus: permission,
                serverStatus: serverHealth,
                lastSuccessAt: successDate,
                lastErrorSummary: firstError
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
