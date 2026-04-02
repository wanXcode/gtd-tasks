import Foundation

struct LocalStore {
    private let fm = FileManager.default

    private var baseDirectory: URL {
        let appSupport = fm.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let dir = appSupport.appendingPathComponent("GTDMenubarSync", isDirectory: true)
        try? fm.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    private var statusURL: URL {
        baseDirectory.appendingPathComponent("status.json")
    }

    func loadStatusSnapshot() -> SyncResultSnapshot? {
        guard let data = try? Data(contentsOf: statusURL) else { return nil }
        return try? JSONDecoder().decode(SyncResultSnapshot.self, from: data)
    }

    func saveStatusSnapshot(_ snapshot: SyncResultSnapshot) {
        guard let data = try? JSONEncoder().encode(snapshot) else { return }
        try? data.write(to: statusURL)
    }
}
