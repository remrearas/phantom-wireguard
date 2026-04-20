import NetworkExtension
import Network
import os.log

/// Independent split-tunnelling provider. Bypass flows for listed
/// apps are pinned to a specific physical interface (Wi-Fi / Ethernet)
/// via `NWConnection.requiredInterface` so they always exit through
/// that NIC — regardless of any active packet tunnel, utun default
/// route or other extension's routing choices.
///
/// The provider does NOT observe `NEPacketTunnelProvider` state. It
/// runs on a single axis: "is the user's exclude list non-empty AND a
/// valid physical interface available?" If the user's chosen interface
/// disappears we cancel the session with an error so the UI reflects
/// the problem; the user explicitly re-picks or re-enables.
final class TransparentProxyProvider: NETransparentProxyProvider {

    private let log = OSLog(
        subsystem: "com.remrearas.Phantom-WG-MacOS.PhantomSplitTunnel",
        category: "proxy"
    )
    private let logger = SplitTunnelLogger.shared
    private let interfaceMonitor = InterfaceMonitor()

    /// Active exclude list, kept in sync with the user's configuration.
    /// We store the full `AppEntry` rather than just signing IDs so the
    /// flow dispatcher can match both the exact signing identifier and
    /// the bundle-ID namespace — the latter is what catches child
    /// processes like `com.brave.Browser.helper` (network service) which
    /// generate flows distinct from the main app.
    private var excludedApps: [AppEntry] = []

    // MARK: - Lifecycle

    override func startProxy(options: [String: Any]? = nil) async throws {
        os_log("startProxy — loading configuration", log: log, type: .default)

        let settings = NETransparentProxyNetworkSettings(tunnelRemoteAddress: "127.0.0.1")
        settings.includedNetworkRules = [
            NENetworkRule(
                remoteNetwork: nil,
                remotePrefix: 0,
                localNetwork: nil,
                localPrefix: 0,
                protocol: .any,
                direction: .outbound
            )
        ]
        try await setTunnelNetworkSettings(settings)

        interfaceMonitor.onChange = { [weak self] interface in
            self?.handleInterfaceChange(interface)
        }
        interfaceMonitor.start()

        // Initial config comes from providerConfiguration — the OS
        // hands us whatever the main app packed via saveToPreferences.
        // No cross-process file or UserDefaults dependency.
        let initialConfig = loadConfigurationFromProviderProtocol() ?? .default
        applyConfiguration(initialConfig)

        os_log("startProxy — ready", log: log, type: .default)
    }

    override func stopProxy(with reason: NEProviderStopReason) async {
        os_log("stopProxy — reason=%{public}d", log: log, type: .default, reason.rawValue)
        interfaceMonitor.stop()
    }

    // MARK: - Flow Dispatch

    override func handleNewFlow(_ flow: NEAppProxyFlow) -> Bool {
        let signingID: String = flow.metaData.sourceAppSigningIdentifier

        if FlowDecisionEngine.isOwnProcess(signingIdentifier: signingID) {
            return false
        }

        guard let matched = matchedExcludeApp(signingID) else {
            return false
        }

        guard let targetInterface = interfaceMonitor.current else {
            logger.log("\(matched.displayName) — bypass unavailable (no physical interface)")
            return false
        }

        logger.log("\(matched.displayName) → \(targetInterface.name)  \(describeFlow(flow))")
        return FlowRelay.relay(flow, appName: matched.displayName, boundTo: targetInterface)
    }

    /// Per-flow summary for LogView. TCP flows carry a single remote
    /// endpoint, so we surface `host:port`; UDP flows dispatch datagrams
    /// to many destinations over the session's lifetime, so at flow
    /// open we can only report the protocol tag.
    private func describeFlow(_ flow: NEAppProxyFlow) -> String {
        if let tcp = flow as? NEAppProxyTCPFlow,
           let endpoint = tcp.remoteEndpoint as? NWHostEndpoint {
            return "TCP  \(endpoint.hostname):\(endpoint.port)"
        }
        if flow is NEAppProxyUDPFlow {
            return "UDP"
        }
        return "?"
    }

    /// Delegates to `FlowDecisionEngine.matches` so the same match
    /// matrix is exercised by main-app unit tests without having to
    /// instantiate a transparent-proxy provider.
    private func matchedExcludeApp(_ signingID: String) -> AppEntry? {
        excludedApps.first { FlowDecisionEngine.matches(signingID: signingID, against: $0) }
    }

    // MARK: - App Messages

    override func handleAppMessage(
        _ messageData: Data,
        completionHandler: ((Data?) -> Void)? = nil
    ) {
        guard let opcode = messageData.first else {
            completionHandler?(nil)
            return
        }

        switch opcode {
        case 0x00:
            // Live reload — config bytes follow the opcode in the
            // same message, so we skip storage entirely and decode
            // inline. Empty payload = fall back to default.
            let configBytes = messageData.dropFirst()
            if configBytes.isEmpty {
                applyConfiguration(.default)
            } else if let config = try? JSONDecoder().decode(
                SplitTunnelingConfiguration.self,
                from: Data(configBytes)
            ) {
                applyConfiguration(config)
            } else {
                os_log("Live reload — decode FAILED, keeping previous config", log: log, type: .error)
            }
            completionHandler?(Data([0x00]))

        case 0x01:
            let payload = logger.snapshot().data(using: .utf8) ?? Data()
            completionHandler?(payload)

        case 0x02:
            // Flush the in-extension log buffer. Auto-purge at the
            // logger's capacity still applies; this is a manual flush.
            logger.clear()
            completionHandler?(Data([0x02]))

        default:
            os_log("Unknown opcode: 0x%02x", log: log, type: .error, opcode)
            completionHandler?(nil)
        }
    }

    // MARK: - Configuration Reload

    /// Apply a decoded configuration to in-memory state + kick the
    /// interface monitor. Centralised so both startup and live reload
    /// go through identical logic.
    private func applyConfiguration(_ configuration: SplitTunnelingConfiguration) {
        excludedApps = configuration.apps
        interfaceMonitor.setSelection(configuration.interfaceSelection)
    }

    /// Read the initial config from the OS-provided
    /// `NETunnelProviderProtocol.providerConfiguration` dict. The main
    /// app packs this at `saveToPreferences()` time; the OS hands it
    /// to the extension during `startProxy()`.
    private func loadConfigurationFromProviderProtocol() -> SplitTunnelingConfiguration? {
        guard let proto = self.protocolConfiguration as? NETunnelProviderProtocol,
              let data = proto.providerConfiguration?["split_config"] as? Data else {
            return nil
        }
        return try? JSONDecoder().decode(SplitTunnelingConfiguration.self, from: data)
    }

    // MARK: - Interface Loss

    /// The user's chosen interface (or any interface in auto mode)
    /// went away. Log it; new flows will be rejected by
    /// `handleNewFlow` (no interface → decline) until the interface
    /// reappears or the user picks a different one.
    private func handleInterfaceChange(_ interface: NWInterface?) {
        if let interface {
            logger.log("interface resolved: \(interface.name) (\(interface.type))")
            return
        }
        logger.log("interface unavailable — new bypass flows will be declined")
    }
}
