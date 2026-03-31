import NetworkExtension

enum NetworkSettingsManager {

    /// Applies excluded routes and IPv6 blackhole for Ghost mode.
    /// - Ghost mode: exclude wstunnel server IPs + blackhole IPv6 (prevent routing loop)
    /// - Standalone: no modifications (WireGuard handles routing as-is)
    static func apply(
        to settings: NEPacketTunnelNetworkSettings,
        excludedIPv4: [String],
        excludedIPv6: [String],
        isGhostMode: Bool
    ) {
        guard isGhostMode else { return }

        // Exclude wstunnel server IPv4
        if let ipv4Settings = settings.ipv4Settings {
            var excluded = ipv4Settings.excludedRoutes ?? []
            for ip in excludedIPv4 {
                excluded.append(NEIPv4Route(destinationAddress: ip, subnetMask: "255.255.255.255"))
                TunnelLogger.log(.tunnel, "Excluded route: \(ip)/32")
            }
            ipv4Settings.excludedRoutes = excluded
        }

        // Blackhole IPv6 — wstunnel starts before routes are applied,
        // so excluded routes alone cannot prevent IPv6 routing loops.
        let ipv6 = NEIPv6Settings(addresses: ["fd00::1"], networkPrefixLengths: [128])
        ipv6.includedRoutes = [NEIPv6Route.default()]
        ipv6.excludedRoutes = []
        settings.ipv6Settings = ipv6
        TunnelLogger.log(.tunnel, "IPv6 blackhole active (Ghost mode)")
    }
}
