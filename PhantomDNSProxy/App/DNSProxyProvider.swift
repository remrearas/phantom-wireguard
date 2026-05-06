import Foundation
import NetworkExtension
import os.log

/// Phase A skeleton — provider boots, logs lifecycle events, declines
/// every flow (no leak protection yet). Real per-app DNS routing arrives
/// in Phase B.
final class DNSProxyProvider: NEDNSProxyProvider {

    private let log = OSLog(
        subsystem: "com.remrearas.Phantom-WG-MacOS.PhantomDNSProxy",
        category: "provider"
    )

    override func startProxy(options: [String: Any]? = nil, completionHandler: @escaping (Error?) -> Void) {
        os_log("startProxy", log: log, type: .default)
        completionHandler(nil)
    }

    override func stopProxy(with reason: NEProviderStopReason, completionHandler: @escaping () -> Void) {
        os_log("stopProxy reason=%{public}d", log: log, type: .default, reason.rawValue)
        completionHandler()
    }

    override func handleNewFlow(_ flow: NEAppProxyFlow) -> Bool {
        // Phase A: pass every query through to the OS default resolver.
        // Per-app rewrite logic ships in Phase B.
        return false
    }
}
