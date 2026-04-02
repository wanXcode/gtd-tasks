import Foundation

enum SyncStatus: String, Codable {
    case idle
    case syncing
    case healthy
    case permissionRequired
    case serverError
    case partialFailure
    case failed

    var displayName: String {
        switch self {
        case .idle: return "空闲"
        case .syncing: return "同步中"
        case .healthy: return "正常"
        case .permissionRequired: return "权限未授权"
        case .serverError: return "服务端异常"
        case .partialFailure: return "部分失败"
        case .failed: return "失败"
        }
    }

    var symbolName: String {
        switch self {
        case .idle: return "checkmark.circle"
        case .syncing: return "arrow.triangle.2.circlepath"
        case .healthy: return "checkmark.circle.fill"
        case .permissionRequired: return "lock.slash"
        case .serverError: return "icloud.slash"
        case .partialFailure: return "exclamationmark.triangle"
        case .failed: return "xmark.octagon"
        }
    }
}

enum ReminderPermissionStatus: String, Codable {
    case authorized
    case denied
    case restricted
    case notDetermined
    case unknown

    var displayName: String {
        switch self {
        case .authorized: return "已授权"
        case .denied: return "已拒绝"
        case .restricted: return "受限"
        case .notDetermined: return "未决定"
        case .unknown: return "未知"
        }
    }
}

enum ServerHealth: String, Codable {
    case online
    case offline
    case degraded
    case unknown

    var displayName: String {
        switch self {
        case .online: return "在线"
        case .offline: return "离线"
        case .degraded: return "异常"
        case .unknown: return "未知"
        }
    }
}

struct SyncResultSnapshot: Codable {
    let status: SyncStatus
    let permissionStatus: ReminderPermissionStatus
    let serverStatus: ServerHealth
    let lastSuccessAt: Date?
    let lastErrorSummary: String?
}

struct SyncStats: Codable {
    let lastKnownChangeID: Int
    let mappingCount: Int
    let lastRunAt: Date?

    static let empty = SyncStats(lastKnownChangeID: 0, mappingCount: 0, lastRunAt: nil)
}
