import AppKit
import Foundation
import ServiceManagement

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
    @Published var launchAtLoginEnabled = false

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
        self.launchAtLoginEnabled = queryLaunchAtLoginEnabled()
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

    func setLaunchAtLoginEnabled(_ enabled: Bool) {
        do {
            if #available(macOS 13.0, *) {
                if enabled {
                    try SMAppService.mainApp.register()
                } else {
                    try SMAppService.mainApp.unregister()
                }
            } else {
                if enabled {
                    try addLoginItemLegacy()
                } else {
                    try removeLoginItemLegacy()
                }
            }
            launchAtLoginEnabled = queryLaunchAtLoginEnabled()
            logger.info("launchAtLogin toggled=\(launchAtLoginEnabled)")
        } catch {
            lastErrorSummary = "修改开机启动失败：\(error.localizedDescription)"
            logger.error("setLaunchAtLoginEnabled failed: \(error.localizedDescription)")
        }
    }

    func openStatusDirectory() {
        NSWorkspace.shared.open(localStore.baseDirectory)
    }

    func openMigrationDoc() {
        let repoRoot = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let doc = repoRoot.appendingPathComponent("docs/macos-sync-migration.md")
        NSWorkspace.shared.open(doc)
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

    private func queryLaunchAtLoginEnabled() -> Bool {
        if #available(macOS 13.0, *) {
            let status = SMAppService.mainApp.status
            return status == .enabled || status == .requiresApproval
        }
        let script = "tell application \"System Events\" to return exists login item \"GTDMenubarSync\""
        return (try? runAppleScript(script).trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == "true") ?? false
    }

    private func addLoginItemLegacy() throws {
        let appPath = (Bundle.main.bundleURL.path as NSString).expandingTildeInPath
        let script = "tell application \"System Events\"\nif not (exists login item \"GTDMenubarSync\") then\nmake login item at end with properties {path:POSIX file \"\(appPath)\" as text, hidden:false, name:\"GTDMenubarSync\"}\nend if\nend tell"
        _ = try runAppleScript(script)
    }

    private func removeLoginItemLegacy() throws {
        let script = "tell application \"System Events\"\nif exists login item \"GTDMenubarSync\" then\ndelete login item \"GTDMenubarSync\"\nend if\nend tell"
        _ = try runAppleScript(script)
    }

    private func runAppleScript(_ source: String) throws -> String {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
        process.arguments = ["-e", source]
        let out = Pipe()
        let err = Pipe()
        process.standardOutput = out
        process.standardError = err
        try process.run()
        process.waitUntilExit()
        let stdout = String(data: out.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        let stderr = String(data: err.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        if process.terminationStatus != 0 {
            throw NSError(domain: "AppleScript", code: Int(process.terminationStatus), userInfo: [NSLocalizedDescriptionKey: stderr.isEmpty ? stdout : stderr])
        }
        return stdout
    }
}
