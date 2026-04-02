import Foundation

@MainActor
final class AppState: ObservableObject {
    @Published var status: SyncStatus = .idle
    @Published var permissionStatus: ReminderPermissionStatus = .unknown
    @Published var serverStatus: ServerHealth = .unknown
    @Published var lastSuccessAt: Date?
    @Published var lastErrorSummary: String?
    @Published var isSyncing = false

    private let permissionManager = PermissionManager()
    private let localStore = LocalStore()
    private lazy var syncEngine = SyncEngine(
        permissionManager: permissionManager,
        serverAPI: ServerAPI(),
        remindersStore: RemindersStore(permissionManager: permissionManager),
        localStore: localStore,
        logger: AppLogger(subsystem: "ai.gtd.menubarsync", category: "sync")
    )

    func bootstrap() async {
        permissionStatus = await permissionManager.currentStatus()
        if let snapshot = localStore.loadStatusSnapshot() {
            self.lastSuccessAt = snapshot.lastSuccessAt
            self.lastErrorSummary = snapshot.lastErrorSummary
            self.serverStatus = snapshot.serverStatus
            self.status = snapshot.status
        }
    }

    func requestPermission() async {
        permissionStatus = await permissionManager.requestAccessIfNeeded()
    }

    func runSyncNow() async {
        guard !isSyncing else { return }
        isSyncing = true
        status = .syncing
        defer { isSyncing = false }

        let result = await syncEngine.runOnce()
        permissionStatus = result.permissionStatus
        serverStatus = result.serverStatus
        lastSuccessAt = result.lastSuccessAt
        lastErrorSummary = result.lastErrorSummary
        status = result.status
        localStore.saveStatusSnapshot(result)
    }
}
