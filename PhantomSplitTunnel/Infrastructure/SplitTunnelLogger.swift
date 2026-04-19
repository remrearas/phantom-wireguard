import Foundation
import os.log

/// Thread-safe in-memory ring buffer for the split-tunnel extension.
/// The main app drains this via `handleAppMessage(0x01)` and renders
/// the lines in the Split-Tunneling sheet's Logs view.
///
/// Matches the shape of the tunnel extension's `TunnelLogger` so the
/// main-app side can reuse its polling abstractions. Everything is
/// behind an `NSLock` — log writes happen from the relay's pump loops
/// and the Main-thread-adjacent `handleAppMessage` reads concurrently.
final class SplitTunnelLogger {

    static let shared = SplitTunnelLogger()

    private let capacity: Int
    private let lock = NSLock()
    private var buffer: [String]
    private let formatter: ISO8601DateFormatter

    private init(capacity: Int = 500) {
        self.capacity = capacity
        self.buffer = []
        self.buffer.reserveCapacity(capacity)
        self.formatter = ISO8601DateFormatter()
        self.formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    }

    // MARK: - Write

    func log(_ message: String) {
        let line = "[\(formatter.string(from: Date()))] \(message)"
        lock.lock()
        if buffer.count >= capacity {
            buffer.removeFirst(buffer.count - capacity + 1)
        }
        buffer.append(line)
        lock.unlock()
    }

    // MARK: - Drain

    /// Returns a newline-joined snapshot. Called by `handleAppMessage`
    /// when the main app requests a dump; does not clear the buffer.
    func snapshot() -> String {
        lock.lock()
        defer { lock.unlock() }
        return buffer.joined(separator: "\n")
    }
}
