import NetworkExtension
import WireGuardKit

class PacketTunnelProvider: NEPacketTunnelProvider {

    private lazy var adapter: WireGuardAdapter = {
        WireGuardAdapter(with: self) { logLevel, message in
            wg_log(logLevel.osLogLevel, message: message)
        }
    }()

    private var wstunnelServerIPv4: [String] = []
    private var wstunnelServerIPv6: [String] = []
    private var isGhostMode = false

    // MARK: - Tunnel Lifecycle

    override func startTunnel(options: [String: NSObject]? = nil) async throws {
        // Flush any residue from a previous session — iOS may reuse
        // the extension process across start/stop cycles, so static
        // state like the ring buffer must be reset explicitly.
        TunnelLogger.clear()
        TunnelLogger.log(.tunnel, "PacketTunnelProvider starting...")

        // 1. Decode config
        guard let proto = protocolConfiguration as? NETunnelProviderProtocol,
              let config = proto.tunnelConfig else {
            TunnelLogger.log(.tunnel, "ERROR: Invalid tunnel configuration")
            throw PacketTunnelProviderError.savedProtocolConfigurationIsInvalid
        }
        TunnelLogger.log(.tunnel, "Config loaded: \(config.name) (\(config.isGhostMode ? "Ghost" : "WireGuard"))")

        isGhostMode = config.isGhostMode

        // 2. Start wstunnel if Ghost mode
        if isGhostMode {
            if let host = config.wstunnel!.url.url.host {
                wstunnelServerIPv4 = DNSResolver.resolveIPv4(host)
                wstunnelServerIPv6 = DNSResolver.resolveIPv6(host)
                TunnelLogger.log(.tunnel, "Wstunnel server resolved: \(host) \u{2192} v4:\(wstunnelServerIPv4) v6:\(wstunnelServerIPv6)")
            }
            try WstunnelLifecycle.start(config: config.wstunnel!)
        }

        // 3. Build WireGuard config
        TunnelLogger.log(.wireGuard, "Building WireGuard config...")
        let tunnelConfiguration: TunnelConfiguration
        do {
            tunnelConfiguration = try WireGuardConfigBuilder.build(
                wireguard: config.wireguard,
                wstunnel: config.wstunnel
            )
        } catch {
            WstunnelLifecycle.stop()
            throw error
        }

        // 4. Start WireGuard adapter
        TunnelLogger.log(.wireGuard, "Starting WireGuard adapter...")
        do {
            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
                adapter.start(tunnelConfiguration: tunnelConfiguration) { error in
                    if let error {
                        TunnelLogger.log(.wireGuard, "ERROR: \(error.localizedDescription)")
                        continuation.resume(throwing: PacketTunnelProviderError.couldNotStartWireGuard)
                    } else {
                        continuation.resume()
                    }
                }
            }
        } catch {
            WstunnelLifecycle.stop()
            throw error
        }

        TunnelLogger.log(.tunnel, "Tunnel active")
    }

    override func stopTunnel(with reason: NEProviderStopReason) async {
        TunnelLogger.log(.tunnel, "Stopping tunnel (reason: \(reason.rawValue))")

        // Stop WireGuard first
        TunnelLogger.log(.wireGuard, "Stopping WireGuard adapter...")
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            adapter.stop { _ in continuation.resume() }
        }
        TunnelLogger.log(.wireGuard, "WireGuard stopped")

        // Then stop wstunnel (idempotent — safe even if standalone)
        WstunnelLifecycle.stop()

        TunnelLogger.log(.tunnel, "Tunnel disconnected")
    }

    // MARK: - App Message

    override func handleAppMessage(_ messageData: Data, completionHandler: ((Data?) -> Void)? = nil) {
        guard let completionHandler else { return }

        guard !messageData.isEmpty else {
            completionHandler(nil)
            return
        }

        switch messageData[0] {
        case 0:
            // WireGuard runtime stats
            adapter.getRuntimeConfiguration { config in
                completionHandler(config?.data(using: .utf8))
            }
        case 1:
            // Log entries (in-memory ring buffer snapshot)
            completionHandler(TunnelLogger.allEntriesAsData())
        case 2:
            // Flush the in-extension log buffer. Auto-purge at
            // maxEntries still applies; this is a manual flush.
            TunnelLogger.clear()
            completionHandler(Data([2]))
        default:
            completionHandler(nil)
        }
    }

    // MARK: - Network Settings Override

    override func setTunnelNetworkSettings(_ tunnelNetworkSettings: NETunnelNetworkSettings?,
                                           completionHandler: ((Error?) -> Void)? = nil) {
        if let settings = tunnelNetworkSettings as? NEPacketTunnelNetworkSettings {
            NetworkSettingsManager.apply(
                to: settings,
                excludedIPv4: wstunnelServerIPv4,
                excludedIPv6: wstunnelServerIPv6,
                isGhostMode: isGhostMode
            )
        }

        super.setTunnelNetworkSettings(tunnelNetworkSettings, completionHandler: completionHandler)
    }
}
