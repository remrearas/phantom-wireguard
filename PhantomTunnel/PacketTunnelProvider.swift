import NetworkExtension
import WireGuardKit
import os.log

private let extLog = OSLog(subsystem: "com.remrearas.Phantom-WG-MacOS.PhantomTunnel", category: "tunnel")

class PacketTunnelProvider: NEPacketTunnelProvider {

    private lazy var adapter: WireGuardAdapter = {
        WireGuardAdapter(with: self) { logLevel, message in
            wg_log(logLevel.osLogLevel, message: message)
        }
    }()

    /// Resolved wstunnel server addresses (for excluded routes)
    private var wstunnelServerIPv4: [String] = []
    private var wstunnelServerIPv6: [String] = []
    private var isGhostMode = false

    // MARK: - Tunnel Lifecycle

    override func startTunnel(
        options: [String: NSObject]?,
        completionHandler: @escaping (Error?) -> Void
    ) {
        os_log("startTunnel called", log: extLog, type: .default)
        TunnelLogger.log(.tunnel, "PacketTunnelProvider starting...")

        // 1. Read config from providerConfiguration (embedded JSON)
        guard let proto = protocolConfiguration as? NETunnelProviderProtocol else {
            os_log("ERROR: protocolConfiguration is not NETunnelProviderProtocol", log: extLog, type: .error)
            completionHandler(PacketTunnelProviderError.savedProtocolConfigurationIsInvalid)
            return
        }

        guard let config = proto.tunnelConfig else {
            let configId = proto.providerConfiguration?["configId"] as? String ?? "nil"
            os_log("ERROR: tunnelConfig is nil (configId: %{public}@)", log: extLog, type: .error, configId)
            TunnelLogger.log(.tunnel, "ERROR: Config decode failed (configId: \(configId))")
            completionHandler(PacketTunnelProviderError.savedProtocolConfigurationIsInvalid)
            return
        }

        os_log("Config loaded: %{public}@", log: extLog, type: .default, config.name)
        TunnelLogger.log(.tunnel, "Config loaded: \(config.name)")

        // 2-3. Wstunnel (Ghost mode only)
        do {
            try startWstunnelIfNeeded(config: config)
        } catch {
            completionHandler(error)
            return
        }

        // 4. Build WireGuard config (IPv4 only, endpoint -> 127.0.0.1:localPort)
        let tunnelConfiguration: TunnelConfiguration
        do {
            tunnelConfiguration = try WireGuardConfigBuilder.build(
                wireguard: config.wireguard, wstunnel: config.wstunnel
            )
        } catch {
            WstunnelLifecycle.stop()
            TunnelLogger.log(.wireGuard, "ERROR: Config build failed - \(error.localizedDescription)")
            completionHandler(error)
            return
        }

        // 5. Start WireGuard adapter
        TunnelLogger.log(.wireGuard, "Starting WireGuard adapter...")
        adapter.start(tunnelConfiguration: tunnelConfiguration) { adapterError in
            if let adapterError {
                WstunnelLifecycle.stop()
                TunnelLogger.log(.wireGuard, "ERROR: \(adapterError.localizedDescription)")
                completionHandler(PacketTunnelProviderError.couldNotStartWireGuard)
            } else {
                TunnelLogger.log(.tunnel, "Tunnel active")
                completionHandler(nil)
            }
        }
    }

    override func stopTunnel(
        with reason: NEProviderStopReason,
        completionHandler: @escaping () -> Void
    ) {
        os_log("stopTunnel called (reason: %d)", log: extLog, type: .default, reason.rawValue)
        TunnelLogger.log(.tunnel, "Stopping tunnel (reason: \(reason.rawValue))")

        adapter.stop { _ in
            WstunnelLifecycle.stop()
            TunnelLogger.log(.tunnel, "Tunnel disconnected")
            completionHandler()

            #if os(macOS)
            exit(0)
            #endif
        }
    }

    // MARK: - Wstunnel

    private func startWstunnelIfNeeded(config: TunnelConfig) throws {
        guard let wstunnel = config.wstunnel else {
            TunnelLogger.log(.tunnel, "Standalone WireGuard mode (no wstunnel)")
            isGhostMode = false
            return
        }

        isGhostMode = true

        if let host = URL(string: wstunnel.url)?.host {
            wstunnelServerIPv4 = DNSResolver.resolveIPv4(host)
            wstunnelServerIPv6 = DNSResolver.resolveIPv6(host)
            TunnelLogger.log(.tunnel, "DNS: \(host) -> v4:\(wstunnelServerIPv4) v6:\(wstunnelServerIPv6)")
        }

        do {
            try WstunnelLifecycle.start(config: wstunnel)
        } catch {
            TunnelLogger.log(.wstunnel, "ERROR: \(error.localizedDescription)")
            throw error
        }
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
            // Log entries (in-memory buffer)
            completionHandler(TunnelLogger.allEntriesAsData())
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
