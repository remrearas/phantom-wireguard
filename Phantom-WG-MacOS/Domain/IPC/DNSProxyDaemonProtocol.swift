import Foundation

/// XPC interface between the PhantomDNSProxy extension (server) and
/// the host app (client). The host pushes configuration updates and
/// drains the daemon's log ring buffer over this channel.
@objc public protocol DNSProxyDaemonProtocol {

    /// JSON-encoded `SplitTunnelingConfiguration` push from the
    /// host app. The daemon forwards to the provider's
    /// `applyConfiguration`.
    func applyConfig(_ data: Data, reply: @escaping (Bool) -> Void)

    /// Newline-joined UTF-8 snapshot of the extension's log ring
    /// buffer, or `nil` when empty.
    func fetchLogs(reply: @escaping (Data?) -> Void)

    /// Manual flush of the ring buffer.
    func clearLogs(reply: @escaping (Bool) -> Void)
}

/// Mach service name registered by the daemon's `NSXPCListener` and
/// looked up by the host app's client. Must literally start with one
/// of the binary's `application-groups` entitlement entries.
public enum DNSProxyDaemonConfig {
    public static let machServiceName = "group.com.remrearas.phantom-wg-macos.dnsproxy"
}
