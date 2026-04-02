import SwiftUI

@main
struct GTDMenubarSyncApp: App {
    @StateObject private var appState = AppState.shared

    init() {
        Task { @MainActor in
            await AppState.shared.bootstrap()
        }
    }

    var body: some Scene {
        MenuBarExtra("GTD Sync", systemImage: appState.status.symbolName) {
            MenuBarRootView()
                .environmentObject(appState)
                .frame(minWidth: 320)
        }
        .menuBarExtraStyle(.window)

        WindowGroup("GTD Sync 权限设置") {
            if appState.shouldShowPermissionWindow {
                PermissionRequestView()
                    .environmentObject(appState)
            } else {
                EmptyView()
            }
        }
        .defaultSize(width: 480, height: 240)
    }
}
