import SwiftUI

@main
struct GTDMenubarSyncApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        MenuBarExtra("GTD Sync", systemImage: appState.status.symbolName) {
            MenuBarRootView()
                .environmentObject(appState)
                .frame(minWidth: 320)
                .task {
                    await appState.bootstrap()
                }
        }
        .menuBarExtraStyle(.window)
    }
}
