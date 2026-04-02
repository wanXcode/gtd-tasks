import AppKit
import Foundation

@MainActor
final class AppState: ObservableObject {
    static let shared = AppState()

    @Published var status: SyncStatus = .idle
    @Published var permissionStatus: ReminderPermissionStatus = .unknown
    @Published var serverStatus: ServerHealth = .unknown
    @Published var lastSuccessAt: Date?
    @Published var lastErrorSummary: String?
    @Published var isSyncing = false
    @Published var stats: SyncStats = .empty
    @Published var autoSyncEnabled = true
    @Published var shouldShowPermissionWindow = false

    private let permissionManager = PermissionManager()
    private let localStore = LocalStore()
    private let logger = AppLogger(subsystem: "ai.gtd.menubarsync", category: "app")
    private var autoSyncTask: Task<Void, Never>?
    private var didBootstrap = false

    private lazy var syncEngine = SyncEngine(
        permissionManager: permissionManager,
        serverAPI: ServerAPI(),
        remindersStore: RemindersStore(permissionManager: permissionManager),
        localStore: localStore,
        logger: AppLogger(subsystem: "ai.gtd.menubarsync", category: "sync")
    )

    private init() {}

    func bootstrap() async {
        guard !didBootstrap else {
            logger.info("bootstrap skipped because already bootstrapped")
            return
        }
        didBootstrap = true
        logger.info("bootstrap started")
        permissionStatus = await permissionManager.currentStatus()
        logger.info("bootstrap permission=\(permissionStatus.rawValue)")
        if let snapshot = localStore.loadStatusSnapshot() {
            self.lastSuccessAt = snapshot.lastSuccessAt
            self.lastErrorSummary = snapshot.lastErrorSummary
            self.serverStatus = snapshot.serverStatus
            self.status = snapshot.status
        }
        self.stats = localStore.loadStats() ?? .empty
        startAutoSyncLoopIfNeeded()
        shouldShowPermissionWindow = permissionStatus != .authorized
        logger.info("bootstrap finished; running first sync without auto-requesting permission")
        await runSyncNow()
    }

    func dismissPermissionWindow() {
        shouldShowPermissionWindow = false
    }

    func requestPermission() async {
        logger.info("requestPermission triggered")
        shouldShowPermissionWindow = true
        NSApplication.shared.activate(ignoringOtherApps: true)
        permissionStatus = await permissionManager.requestAccessIfNeeded()
        logger.info("requestPermission result=\(permissionStatus.rawValue)")
        if permissionStatus == .authorized {
            shouldShowPermissionWindow = false
            lastErrorSummary = nil
            if status == .permissionRequired {
                status = .idle
            }
            await runSyncNow()
        } else {
            lastErrorSummary = "尚未获得 Reminders 权限，请检查系统弹窗或系统设置"
            status = .permissionRequired
        }
    }

    func setAutoSyncEnabled(_ enabled: Bool) {
        autoSyncEnabled = enabled
        logger.info("autoSync toggled=\(enabled)")
        if enabled {
            startAutoSyncLoopIfNeeded()
        } else {
            autoSyncTask?.cancel()
            autoSyncTask = nil
        }
    }

    func runSyncNow() async {
        guard !isSyncing else {
            logger.info("runSyncNow skipped because already syncing")
            return
        }
        isSyncing = true
        status = .syncing
        logger.info("runSyncNow started")
        defer {
            isSyncing = false
            logger.info("runSyncNow ended with status=\(status.rawValue)")
        }

        let result = await syncEngine.runOnce()
        permissionStatus = result.permissionStatus
        serverStatus = result.serverStatus
        lastSuccessAt = result.lastSuccessAt
        lastErrorSummary = result.lastErrorSummary
        status = result.status
        if permissionStatus == .authorized {
            shouldShowPermissionWindow = false
        }
        localStore.saveStatusSnapshot(result)
        stats = localStore.loadStats() ?? stats
    }

    private func startAutoSyncLoopIfNeeded() {
        guard autoSyncEnabled, autoSyncTask == nil else { return }
        logger.info("starting auto sync loop")
        autoSyncTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(60))
                guard let self, self.autoSyncEnabled else { continue }
                await self.runSyncNow()
            }
        }
    }
}
