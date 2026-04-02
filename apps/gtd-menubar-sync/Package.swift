// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "GTDMenubarSync",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "GTDMenubarSync", targets: ["GTDMenubarSync"])
    ],
    targets: [
        .executableTarget(
            name: "GTDMenubarSync",
            path: "Sources/GTDMenubarSync"
        )
    ]
)
