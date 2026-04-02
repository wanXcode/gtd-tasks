import SwiftUI

struct MenuBarRootView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("GTD Menubar Sync")
                .font(.headline)

            StatusSectionView(
                title: "同步状态",
                value: appState.status.displayName,
                symbol: appState.status.symbolName
            )

            StatusSectionView(
                title: "Reminders 权限",
                value: appState.permissionStatus.displayName,
                symbol: "checkmark.shield"
            )

            StatusSectionView(
                title: "服务端",
                value: appState.serverStatus.displayName,
                symbol: "network"
            )

            if let lastSuccessAt = appState.lastSuccessAt {
                Text("上次成功同步：\(lastSuccessAt.formatted(date: .numeric, time: .standard))")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if let lastErrorSummary = appState.lastErrorSummary, !lastErrorSummary.isEmpty {
                Text("最近错误：\(lastErrorSummary)")
                    .font(.caption)
                    .foregroundStyle(.orange)
            }

            Divider()

            HStack {
                Button("立即同步") {
                    Task { await appState.runSyncNow() }
                }
                .disabled(appState.isSyncing)

                Button("请求权限") {
                    Task { await appState.requestPermission() }
                }
            }

            Divider()

            Button("退出") {
                NSApplication.shared.terminate(nil)
            }
        }
        .padding(14)
    }
}
