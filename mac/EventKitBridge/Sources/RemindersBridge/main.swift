import Foundation

let args = CommandLine.arguments.dropFirst()

guard let action = args.first else {
    JsonIO.printJSON(BridgeError(action: "unknown", error_code: "MISSING_ACTION", error_message: "action is required"))
    exit(1)
}

var inputJSON: String?
var index = 1
while index < args.count {
    let token = Array(args)[index]
    if token == "--input-json", index + 1 < args.count {
        inputJSON = Array(args)[index + 1]
        index += 2
        continue
    }
    index += 1
}

let payload = JsonIO.decodePayload(inputJSON)
let service = EventKitService()

switch action {
case "check-permission":
    JsonIO.printJSON(service.checkPermission())
case "list-calendars":
    JsonIO.printJSON(service.listCalendars())
case "preflight":
    JsonIO.printJSON(service.preflight(payload))
case "get":
    switch service.get(payload) {
    case .success(let ok): JsonIO.printJSON(ok)
    case .failure(let err): JsonIO.printJSON(err); exit(1)
    }
case "create":
    switch service.create(payload) {
    case .success(let ok): JsonIO.printJSON(ok)
    case .failure(let err): JsonIO.printJSON(err); exit(1)
    }
case "update":
    switch service.update(payload) {
    case .success(let ok): JsonIO.printJSON(ok)
    case .failure(let err): JsonIO.printJSON(err); exit(1)
    }
case "move":
    switch service.move(payload) {
    case .success(let ok): JsonIO.printJSON(ok)
    case .failure(let err): JsonIO.printJSON(err); exit(1)
    }
case "complete":
    switch service.complete(payload) {
    case .success(let ok): JsonIO.printJSON(ok)
    case .failure(let err): JsonIO.printJSON(err); exit(1)
    }
case "delete":
    switch service.delete(payload) {
    case .success(let ok): JsonIO.printJSON(ok)
    case .failure(let err): JsonIO.printJSON(err); exit(1)
    }
default:
    JsonIO.printJSON(BridgeError(action: action, error_code: "UNKNOWN_ACTION", error_message: "unsupported action: \(action)"))
    exit(1)
}
