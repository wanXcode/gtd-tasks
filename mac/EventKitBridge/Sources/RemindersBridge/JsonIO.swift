import Foundation

enum JsonIO {
    static func printJSON<T: Encodable>(_ value: T) {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.withoutEscapingSlashes]
        do {
            let data = try encoder.encode(value)
            if let text = String(data: data, encoding: .utf8) {
                print(text)
            } else {
                fputs("{\"success\":false,\"action\":\"unknown\",\"error_code\":\"ENCODING_FAILED\",\"error_message\":\"utf8 encoding failed\"}\n", stderr)
            }
        } catch {
            fputs("{\"success\":false,\"action\":\"unknown\",\"error_code\":\"ENCODE_FAILED\",\"error_message\":\"", stderr)
            fputs(error.localizedDescription, stderr)
            fputs("\"}\n", stderr)
        }
    }

    static func decodePayload(_ raw: String?) -> ReminderPayload? {
        guard let raw, !raw.isEmpty else { return nil }
        guard let data = raw.data(using: .utf8) else { return nil }
        return try? JSONDecoder().decode(ReminderPayload.self, from: data)
    }
}
