import SwiftUI

struct PermissionRequestView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("需要 Reminders 权限")
                .font(.title2)
                .bold()

            Text("GTD Menubar Sync 需要访问 Apple Reminders，才能把线上任务同步到本地提醒事项。")
                .fixedSize(horizontal: false, vertical: true)

            Text("请点击下方按钮发起授权请求。如果系统仍未弹窗，后续我会继续排查签名或主体配置问题。")
                .font(.callout)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            HStack {
                Button("请求 Reminders 权限") {
                    Task { await appState.requestPermission() }
                }
                .keyboardShortcut(.defaultAction)

                Button("稍后再说") {
                    appState.dismissPermissionWindow()
                }
            }

            if let lastErrorSummary = appState.lastErrorSummary, !lastErrorSummary.isEmpty {
                Divider()
                Text("最近错误：\(lastErrorSummary)")
                    .font(.caption)
                    .foregroundStyle(.orange)
            }
        }
        .padding(20)
        .frame(width: 460)
    }
}
