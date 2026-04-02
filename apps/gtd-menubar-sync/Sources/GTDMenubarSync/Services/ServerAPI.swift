import Foundation

struct ServerAPI {
    var baseURL: URL = URL(string: ProcessInfo.processInfo.environment["GTD_API_BASE_URL"] ?? "https://gtd.5666.net")!

    private func request(path: String, method: String = "GET", body: Data? = nil) async throws -> (Data, HTTPURLResponse) {
        let url = URL(string: path, relativeTo: baseURL)!
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 60
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw NSError(domain: "ServerAPI", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid response"])
        }
        guard (200..<300).contains(http.statusCode) else {
            throw NSError(domain: "ServerAPI", code: http.statusCode, userInfo: [NSLocalizedDescriptionKey: String(data: data, encoding: .utf8) ?? "HTTP \(http.statusCode)"])
        }
        return (data, http)
    }

    func healthcheck() async -> ServerHealth {
        do {
            let (_, response) = try await request(path: "/api/tasks?status=open&limit=1")
            return (200..<300).contains(response.statusCode) ? .online : .degraded
        } catch {
            return .offline
        }
    }

    func fetchChanges(since changeID: Int, limit: Int = 100) async throws -> GTDChangesResponse {
        let (data, _) = try await request(path: "/api/changes?since_change_id=\(changeID)&limit=\(limit)")
        return try JSONDecoder().decode(GTDChangesResponse.self, from: data)
    }

    func fetchOpenTasks(limit: Int = 1000) async throws -> GTDTasksResponse {
        let (data, _) = try await request(path: "/api/tasks?status=open&limit=\(limit)")
        return try JSONDecoder().decode(GTDTasksResponse.self, from: data)
    }

    func fetchMappings() async throws -> AppleMappingsResponse {
        let (data, _) = try await request(path: "/api/apple/mappings")
        return try JSONDecoder().decode(AppleMappingsResponse.self, from: data)
    }

    func saveMappings(_ mappings: [AppleMappingItem]) async throws {
        let payload = ["mappings": mappings.map { ["task_id": $0.taskID, "apple_reminder_id": $0.appleReminderID] }]
        let body = try JSONSerialization.data(withJSONObject: payload)
        _ = try await request(path: "/api/apple/mappings", method: "POST", body: body)
    }

    func ackChanges(clientID: String, lastChangeID: Int) async throws {
        let payload: [String: Any] = [
            "last_change_id": lastChangeID,
            "client_type": "mac-menubar",
            "meta": ["hostname": Host.current().localizedName ?? "mac-local"]
        ]
        let body = try JSONSerialization.data(withJSONObject: payload)
        _ = try await request(path: "/api/sync/clients/\(clientID)/ack", method: "POST", body: body)
    }
}
