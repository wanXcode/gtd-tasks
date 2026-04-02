import Foundation

struct LocalStore {
    private let fm = FileManager.default
    private let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }()
    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()

    var baseDirectory: URL {
        let appSupport = fm.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let dir = appSupport.appendingPathComponent("GTDMenubarSync", isDirectory: true)
        try? fm.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    private var statusURL: URL { baseDirectory.appendingPathComponent("status.json") }
    private var stateURL: URL { baseDirectory.appendingPathComponent("state.json") }
    private var mappingsURL: URL { baseDirectory.appendingPathComponent("mappings.json") }
    private var statsURL: URL { baseDirectory.appendingPathComponent("stats.json") }

    func loadStatusSnapshot() -> SyncResultSnapshot? {
        guard let data = try? Data(contentsOf: statusURL) else { return nil }
        return try? decoder.decode(SyncResultSnapshot.self, from: data)
    }

    func saveStatusSnapshot(_ snapshot: SyncResultSnapshot) {
        guard let data = try? encoder.encode(snapshot) else { return }
        try? data.write(to: statusURL)
    }

    func loadClientState() -> SyncClientState? {
        guard let data = try? Data(contentsOf: stateURL) else { return nil }
        return try? decoder.decode(SyncClientState.self, from: data)
    }

    func saveClientState(_ state: SyncClientState) {
        guard let data = try? encoder.encode(state) else { return }
        try? data.write(to: stateURL)
    }

    func loadMappings() -> [String: String] {
        guard let data = try? Data(contentsOf: mappingsURL) else { return [:] }
        return (try? decoder.decode([String: String].self, from: data)) ?? [:]
    }

    func saveMappings(_ mappings: [String: String]) {
        guard let data = try? encoder.encode(mappings) else { return }
        try? data.write(to: mappingsURL)
    }

    func loadStats() -> SyncStats? {
        guard let data = try? Data(contentsOf: statsURL) else { return nil }
        return try? decoder.decode(SyncStats.self, from: data)
    }

    func saveStats(_ stats: SyncStats) {
        guard let data = try? encoder.encode(stats) else { return }
        try? data.write(to: statsURL)
    }
}
