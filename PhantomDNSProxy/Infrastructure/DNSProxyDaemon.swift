import Foundation
import os.log

/// In-process XPC server inside PhantomDNSProxy. Singleton, tied to
/// the extension process lifetime — outlives provider start/stop
/// cycles. Buffers `applyConfig` payloads when no provider is
/// attached so the lazy-spawn window doesn't drop config.
final class DNSProxyDaemon: NSObject, NSXPCListenerDelegate, DNSProxyDaemonProtocol {

    static let shared = DNSProxyDaemon()

    private let log = OSLog(
        subsystem: "com.remrearas.Phantom-WG-MacOS.PhantomDNSProxy",
        category: "daemon"
    )

    private let listener: NSXPCListener
    private(set) var isStarted = false

    /// Live provider attached via `attach(provider:)` at `startProxy`.
    /// Weak so `stopProxy` doesn't leave a dangling pointer.
    private weak var provider: DNSProxyProvider?

    /// Last `applyConfig` payload buffered while no provider was
    /// attached. Replayed at the next `attach()`. Cleared on apply,
    /// on detach, and overwritten by any subsequent push.
    private var pendingConfig: Data?
    private let pendingLock = NSLock()

    private override init() {
        self.listener = NSXPCListener(machServiceName: DNSProxyDaemonConfig.machServiceName)
        super.init()
        self.listener.delegate = self
    }

    /// Provider lifecycle hook called from `startProxy`. Drains any
    /// `pendingConfig` buffered during the lazy-spawn window so the
    /// provider boots with the live App-pushed payload instead of
    /// the stale `providerConfiguration` bootstrap.
    func attach(provider: DNSProxyProvider) {
        self.provider = provider
        os_log("provider attached", log: log, type: .default)

        pendingLock.lock()
        let data = pendingConfig
        pendingConfig = nil
        pendingLock.unlock()

        guard let data else { return }
        do {
            let config = try JSONDecoder().decode(SplitTunnelingConfiguration.self, from: data)
            provider.applyConfiguration(config)
            os_log("attach: drained pending config — apps=%{public}d",
                   log: log, type: .default, config.apps.count)
        } catch {
            os_log("attach: pending config decode FAILED — %{public}@",
                   log: log, type: .error, error.localizedDescription)
        }
    }

    /// Drops the provider reference and clears the in-memory log
    /// buffer so the next session starts with a fresh log surface
    /// (matching SplitTunnel's session-bound log semantics).
    func detach() {
        self.provider = nil
        pendingLock.lock()
        pendingConfig = nil
        pendingLock.unlock()
        RingBufferLogger.shared.clear()
        os_log("provider detached, log buffer cleared", log: log, type: .default)
    }

    /// Resume the listener. Idempotent. Must run before any client
    /// attempts a connection.
    func start() {
        guard !isStarted else {
            os_log("daemon.start() already started, skipping",
                   log: log, type: .default)
            return
        }
        listener.resume()
        isStarted = true
        os_log("daemon listening on %{public}@",
               log: log, type: .default, DNSProxyDaemonConfig.machServiceName)
    }

    func stop() {
        guard isStarted else { return }
        listener.invalidate()
        isStarted = false
        os_log("daemon stopped", log: log, type: .default)
    }

    // MARK: - NSXPCListenerDelegate

    func listener(
        _ listener: NSXPCListener,
        shouldAcceptNewConnection newConnection: NSXPCConnection
    ) -> Bool {
        let pid = newConnection.processIdentifier
        os_log("accepting connection pid=%{public}d",
               log: log, type: .default, pid)

        newConnection.exportedInterface = NSXPCInterface(with: DNSProxyDaemonProtocol.self)
        newConnection.exportedObject = self
        newConnection.invalidationHandler = { [weak self] in
            os_log("connection invalidated pid=%{public}d",
                   log: self?.log ?? OSLog.default, type: .default, pid)
        }
        newConnection.interruptionHandler = { [weak self] in
            os_log("connection interrupted pid=%{public}d",
                   log: self?.log ?? OSLog.default, type: .default, pid)
        }
        newConnection.resume()
        return true
    }

    // MARK: - DNSProxyDaemonProtocol

    /// Buffers the payload when no provider is attached (lazy-spawn
    /// window) and replies `true` so the App's client considers the
    /// push successful — `attach` drains the buffer before the
    /// provider sees its first flow.
    func applyConfig(_ data: Data, reply: @escaping (Bool) -> Void) {
        os_log("RPC applyConfig (%{public}d bytes)",
               log: log, type: .default, data.count)

        guard let provider = provider else {
            pendingLock.lock()
            pendingConfig = data
            pendingLock.unlock()
            os_log("applyConfig — no provider yet, buffered for attach",
                   log: log, type: .default)
            reply(true)
            return
        }

        do {
            let config = try JSONDecoder().decode(SplitTunnelingConfiguration.self, from: data)
            provider.applyConfiguration(config)
            os_log("applyConfig — applied apps=%{public}d",
                   log: log, type: .default, config.apps.count)
            reply(true)
        } catch {
            os_log("applyConfig — decode FAILED: %{public}@",
                   log: log, type: .error, error.localizedDescription)
            reply(false)
        }
    }

    func fetchLogs(reply: @escaping (Data?) -> Void) {
        let snapshot = RingBufferLogger.shared.snapshot()
        if snapshot.isEmpty {
            reply(nil)
            return
        }
        reply(snapshot.data(using: .utf8))
    }

    func clearLogs(reply: @escaping (Bool) -> Void) {
        os_log("RPC clearLogs", log: log, type: .default)
        RingBufferLogger.shared.clear()
        reply(true)
    }
}
