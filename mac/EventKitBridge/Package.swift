// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "EventKitBridge",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "reminders-bridge", targets: ["RemindersBridge"])
    ],
    targets: [
        .executableTarget(
            name: "RemindersBridge",
            path: "Sources/RemindersBridge"
        )
    ]
)
