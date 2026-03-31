import Foundation
import Network
import WireGuardKit

enum WireGuardConfigBuilder {

    /// Converts WireguardConfig + optional WstunnelConfig into WireGuardKit's TunnelConfiguration.
    /// - Ghost mode: endpoint overridden to 127.0.0.1:localPort (wstunnel proxy)
    /// - Standalone: endpoint used as-is from peer config
    /// - Filters to IPv4-only addresses and AllowedIPs
    static func build(wireguard: WireguardConfig, wstunnel: WstunnelConfig?) throws -> TunnelConfiguration {
        let interfaceConfig = try buildInterface(from: wireguard)
        let peerConfig = try buildPeer(from: wireguard, wstunnel: wstunnel)

        return TunnelConfiguration(
            name: nil,
            interface: interfaceConfig,
            peers: [peerConfig]
        )
    }

    // MARK: - Private

    private static func buildInterface(from config: WireguardConfig) throws -> InterfaceConfiguration {
        guard let privateKey = PrivateKey(base64Key: config.interface.privateKey) else {
            TunnelLogger.log(.wireGuard, "ERROR: Invalid private key")
            throw PacketTunnelProviderError.savedProtocolConfigurationIsInvalid
        }

        var iface = InterfaceConfiguration(privateKey: privateKey)

        let allAddresses = config.interface.address
            .components(separatedBy: ",")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .compactMap { IPAddressRange(from: $0) }

        iface.addresses = allAddresses

        guard !iface.addresses.isEmpty else {
            TunnelLogger.log(.wireGuard, "ERROR: No valid addresses")
            throw PacketTunnelProviderError.savedProtocolConfigurationIsInvalid
        }

        TunnelLogger.log(.wireGuard, "Interface addresses: \(iface.addresses.map { $0.stringRepresentation })")

        iface.dns = config.interface.dns
            .components(separatedBy: ",")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .compactMap { DNSServer(from: $0) }

        if config.interface.mtu > 0 {
            iface.mtu = UInt16(clamping: config.interface.mtu)
        }

        return iface
    }

    private static func buildPeer(from config: WireguardConfig, wstunnel: WstunnelConfig?) throws -> PeerConfiguration {
        guard let publicKey = PublicKey(base64Key: config.peer.publicKey) else {
            TunnelLogger.log(.wireGuard, "ERROR: Invalid public key")
            throw PacketTunnelProviderError.savedProtocolConfigurationIsInvalid
        }

        var peer = PeerConfiguration(publicKey: publicKey)

        if let psk = config.peer.presharedKey, !psk.isEmpty,
           let preSharedKey = PreSharedKey(base64Key: psk) {
            peer.preSharedKey = preSharedKey
        }

        let allAllowedIPs = config.peer.allowedIPs
            .components(separatedBy: ",")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .compactMap { IPAddressRange(from: $0) }

        peer.allowedIPs = allAllowedIPs

        TunnelLogger.log(.wireGuard, "AllowedIPs: \(peer.allowedIPs.count) entries")

        // Endpoint: Ghost mode -> wstunnel proxy, standalone -> direct
        let endpointString: String
        if let ws = wstunnel {
            endpointString = "127.0.0.1:\(ws.localPort)"
            TunnelLogger.log(.wireGuard, "Endpoint override (Ghost): \(endpointString)")
        } else {
            endpointString = config.peer.endpoint
            TunnelLogger.log(.wireGuard, "Endpoint (standalone): \(endpointString)")
        }

        guard let endpoint = Endpoint(from: endpointString) else {
            TunnelLogger.log(.wireGuard, "ERROR: Invalid endpoint: \(endpointString)")
            throw PacketTunnelProviderError.savedProtocolConfigurationIsInvalid
        }
        peer.endpoint = endpoint

        if config.peer.persistentKeepalive > 0 {
            peer.persistentKeepAlive = UInt16(clamping: config.peer.persistentKeepalive)
        }

        return peer
    }
}
