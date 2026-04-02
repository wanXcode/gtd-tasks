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

            StatusSectionView(
                title: "最后 change 游标",
                value: String(appState.stats.lastKnownChangeID),
                symbol: "point.topleft.down.curvedto.point.bottomright.up"
            )

            StatusSectionView(
                title: "本地 mapping 数量",
                value: String(appState.stats.mappingCount),
                symbol: "link"
            )

            if let lastSuccessAt = appState.lastSuccessAt {
                Text("上次成功同步：\(lastSuccessAt.formatted(date: .numeric, time: .standard))")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if let lastRunAt = appState.stats.lastRunAt {
                Text("最近一次运行：\(lastRunAt.formatted(date: .numeric, time: .standard))")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if let lastErrorSummary = appState.lastErrorSummary, !lastErrorSummary.isEmpty {
                Text("最近错误：\(lastErrorSummary)")
                    .font(.caption)
                    .foregroundStyle(.orange)
            }

            Toggle("自动同步（60 秒）", isOn: Binding(
                get: { appState.autoSyncEnabled },
                set: { appState.setAutoSyncEnabled($0) }
            ))

            Toggle("开机启动", isOn: Binding(
                get: { appState.launchAtLoginEnabled },
                set: { appState.setLaunchAtLoginEnabled($0) }
            ))

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

            HStack {
                Button("打开状态目录") {
                    appState.openStatusDirectory()
                }
                Button("打开迁移文档") {
                    appState.openMigrationDoc()
                }
            }

            Text("提示：请在点击“请求权限”后观察系统弹窗。")
                .font(.caption2)
                .foregroundStyle(.secondary)

            Divider()

            Button("退出") {
                NSApplication.shared.terminate(nil)
            }
        }
        .padding(14)
    }
}
