import NetworkExtension
import os.log

/// Phase 1 skeleton. The transparent proxy is installed and activated
/// so the full install/approve/remove UX can be validated end-to-end,
/// but the decision engine is intentionally absent — every new flow is
/// handed straight back to the OS (`return false`) and routed through
/// the default path (tunnel when one is active, physical interface
/// otherwise). Flow classification + relay lands in Phase 2.
final class TransparentProxyProvider: NETransparentProxyProvider {

    private let log = OSLog(
        subsystem: "com.remrearas.Phantom-WG-MacOS.PhantomSplitTunnel",
        category: "proxy"
    )

    override func startProxy(options: [String: Any]? = nil) async throws {
        os_log("startProxy — skeleton no-op mode", log: log, type: .default)

        let settings = NETransparentProxyNetworkSettings(tunnelRemoteAddress: "127.0.0.1")
        // Subscribe to every outbound flow. Phase 2 uses the signing
        // identifier on each flow to classify bypass vs. tunnel.
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
        os_log("startProxy — network settings applied", log: log, type: .default)
    }

    override func stopProxy(with reason: NEProviderStopReason) async {
        os_log("stopProxy — reason=%{public}d", log: log, type: .default, reason.rawValue)
    }

    override func handleNewFlow(_ flow: NEAppProxyFlow) -> Bool {
        // Phase 1: decline every flow so the OS picks the default route.
        // Phase 2 replaces this with a FlowDecisionEngine lookup +
        // FlowRelay dispatch for the bypass branch.
        return false
    }
}
