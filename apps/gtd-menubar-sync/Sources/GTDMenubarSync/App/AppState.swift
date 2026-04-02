import Foundation

@MainActor
final class AppState: ObservableObject {
    @Published var status: SyncStatus = .idle
    @Published var permissionStatus: ReminderPermissionStatus = .unknown
    @Published var serverStatus: ServerHealth = .unknown
    @Published var lastSuccessAt: Date?
    @Published var lastErrorSummary: String?
    @Published var isSyncing = false
    @Published var stats: SyncStats = .empty
    @Published var autoSyncEnabled = true

    private let permissionManager = PermissionManager()
    private let localStore = LocalStore()
    private var autoSyncTask: Task<Void, Never>?

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
        self.stats = localStore.loadStats() ?? .empty
        startAutoSyncLoopIfNeeded()
    }

    func requestPermission() async {
        permissionStatus = await permissionManager.requestAccessIfNeeded()
    }

    func setAutoSyncEnabled(_ enabled: Bool) {
        autoSyncEnabled = enabled
        if enabled {
            startAutoSyncLoopIfNeeded()
        } else {
            autoSyncTask?.cancel()
            autoSyncTask = nil
        }
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
        stats = localStore.loadStats() ?? stats
    }

    private func startAutoSyncLoopIfNeeded() {
        guard autoSyncEnabled, autoSyncTask == nil else { return }
        autoSyncTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(60))
                guard let self, self.autoSyncEnabled else { continue }
                await self.runSyncNow()
            }
        }
    }
}
