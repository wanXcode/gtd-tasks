import Foundation

struct ServerAPI {
    var baseURL: URL = URL(string: ProcessInfo.processInfo.environment["GTD_API_BASE_URL"] ?? "https://gtd.5666.net")!

    func healthcheck() async -> ServerHealth {
        guard let url = URL(string: "/api/tasks?status=open&limit=1", relativeTo: baseURL) else {
            return .offline
        }

        do {
            let (_, response) = try await URLSession.shared.data(from: url)
            guard let http = response as? HTTPURLResponse else { return .degraded }
            return (200..<300).contains(http.statusCode) ? .online : .degraded
        } catch {
            return .offline
        }
    }
}
