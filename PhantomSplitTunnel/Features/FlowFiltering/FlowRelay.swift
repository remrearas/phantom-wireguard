import Network
import NetworkExtension
import os.log

/// Entry point for bypass flows. Dispatches the flow to the
/// appropriate concrete relay, passing along the physical interface
/// the relay must bind its outbound `NWConnection` to. That binding
/// is what keeps bypass traffic off the tunnel's utun interface.
enum FlowRelay {

    static let log = OSLog(
        subsystem: "com.remrearas.Phantom-WG-MacOS.PhantomSplitTunnel",
        category: "relay"
    )

    /// Dispatch the flow to the correct concrete relay. Returns `true`
    /// so the caller's `handleNewFlow` can return `true` (we claim it).
    /// `appName` is used by the relay when logging a flow failure so the
    /// user sees which app's connection broke and why.
    static func relay(_ flow: NEAppProxyFlow, appName: String, boundTo interface: NWInterface) -> Bool {
        if let tcp = flow as? NEAppProxyTCPFlow {
            TCPFlowRelay(flow: tcp, interface: interface, appName: appName).start()
            return true
        }
        if let udp = flow as? NEAppProxyUDPFlow {
            UDPFlowRelay(flow: udp, interface: interface, appName: appName).start()
            return true
        }
        os_log("Unknown flow type — declining", log: log, type: .error)
        return false
    }
}
