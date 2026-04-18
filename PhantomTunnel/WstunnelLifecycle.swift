import Foundation

enum WstunnelLifecycle {

    private static var isStarted = false

    /// Starts the wstunnel local UDP proxy with the given configuration.
    /// All fields are pre-validated by `WstunnelConfig`'s typed init —
    /// non-empty URL, resolvable host, and ports in the UInt16 range
    /// are guaranteed at this point.
    static func start(config: WstunnelConfig) throws {
        guard !config.remoteHost.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            SharedLogger.log(.wstunnel, "ERROR: empty remoteHost")
            throw PacketTunnelProviderError.invalidWstunnelConfig
        }

        SharedLogger.log(.wstunnel, "Starting wstunnel...")
        SharedLogger.log(.wstunnel, "Remote: \(config.url.textual)")
        SharedLogger.log(.wstunnel, "Local proxy: \(config.localHost):\(config.localPort)")
        SharedLogger.log(.wstunnel, "Forward to: \(config.remoteHost):\(config.remotePort)")

        WstunnelBridge.setLogCallback { _, message in
            SharedLogger.log(.wstunnel, message)
        }
        WstunnelBridge.initLogging(level: .info)
        SharedLogger.log(.wstunnel, "Version: \(WstunnelBridge.version)")

        do {
            let wsConfig = WstunnelBridge.Config()
            try wsConfig.setRemoteURL(config.url.textual)
            try wsConfig.setHTTPUpgradePathPrefix(config.secret)
            try wsConfig.addTunnelUDP(
                localPort: config.localPort,
                remoteHost: config.remoteHost,
                remotePort: config.remotePort
            )
            try wsConfig.start()
            isStarted = true
            SharedLogger.log(.wstunnel, "Wstunnel started (running: \(WstunnelBridge.isRunning))")
        } catch {
            SharedLogger.log(.wstunnel, "ERROR: \(error.localizedDescription)")
            if let lastErr = WstunnelBridge.lastError {
                SharedLogger.log(.wstunnel, "Detail: \(lastErr)")
            }
            throw PacketTunnelProviderError.couldNotStartWstunnel
        }
    }

    /// Stops the wstunnel proxy. Idempotent — safe to call multiple times.
    static func stop() {
        guard isStarted else { return }
        isStarted = false

        SharedLogger.log(.wstunnel, "Stopping wstunnel...")
        do {
            try WstunnelBridge.stop()
            SharedLogger.log(.wstunnel, "Wstunnel stopped")
        } catch {
            SharedLogger.log(.wstunnel, "Stop error: \(error.localizedDescription)")
        }
    }
}
