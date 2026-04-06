import Foundation
import Network
import WireGuardKit

enum WireGuardConfigBuilder {

    /// Converts WireguardConfig + optional WstunnelConfig into WireGuardKit's TunnelConfiguration.
    /// - Filters to IPv4-only addresses and AllowedIPs (iOS routing constraint)
    /// - Ghost mode: overrides endpoint to 127.0.0.1:localPort (wstunnel proxy)
    /// - Standalone: uses peer endpoint directly
    static func build(wireguard: WireguardConfig, wstunnel: WstunnelConfig?) throws -> TunnelConfiguration {
        let interfaceConfig = try buildInterface(from: wireguard)
        let peerConfig = try buildPeer(from: wireguard, wstunnel: wstunnel)

        return TunnelConfiguration(
            name: nil,
            interface: interfaceConfig,
            peers: [peerConfig]
        )
    }

    // MARK: - Interface

    private static func buildInterface(from wireguard: WireguardConfig) throws -> InterfaceConfiguration {
        guard let privateKey = PrivateKey(base64Key: wireguard.interface.privateKey) else {
            SharedLogger.log(.wireGuard, "ERROR: Invalid private key")
            throw PacketTunnelProviderError.savedProtocolConfigurationIsInvalid
        }

        var config = InterfaceConfiguration(privateKey: privateKey)

        config.addresses = wireguard.interface.address
            .components(separatedBy: ",")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .compactMap { IPAddressRange(from: $0) }
            .filter { $0.address is IPv4Address }

        guard !config.addresses.isEmpty else {
            SharedLogger.log(.wireGuard, "ERROR: No valid IPv4 addresses")
            throw PacketTunnelProviderError.savedProtocolConfigurationIsInvalid
        }

        SharedLogger.log(.wireGuard, "Interface addresses (IPv4 only): \(config.addresses.map { $0.stringRepresentation })")

        config.dns = wireguard.interface.dns
            .components(separatedBy: ",")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .compactMap { DNSServer(from: $0) }

        if wireguard.interface.mtu > 0 {
            config.mtu = UInt16(clamping: wireguard.interface.mtu)
        }

        return config
    }

    // MARK: - Peer

    private static func buildPeer(from wireguard: WireguardConfig, wstunnel: WstunnelConfig?) throws -> PeerConfiguration {
        guard let publicKey = PublicKey(base64Key: wireguard.peer.publicKey) else {
            SharedLogger.log(.wireGuard, "ERROR: Invalid public key")
            throw PacketTunnelProviderError.savedProtocolConfigurationIsInvalid
        }

        var config = PeerConfiguration(publicKey: publicKey)

        if let psk = wireguard.peer.presharedKey, !psk.isEmpty,
           let preSharedKey = PreSharedKey(base64Key: psk) {
            config.preSharedKey = preSharedKey
        }

        config.allowedIPs = wireguard.peer.allowedIPs
            .components(separatedBy: ",")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .compactMap { IPAddressRange(from: $0) }
            .filter { $0.address is IPv4Address }

        SharedLogger.log(.wireGuard, "AllowedIPs (IPv4 only): \(config.allowedIPs.count) entries")

        // Endpoint: Ghost mode → wstunnel proxy, standalone → direct
        let endpointString: String
        if let ws = wstunnel {
            endpointString = "127.0.0.1:\(ws.localPort)"
            SharedLogger.log(.wireGuard, "Endpoint override (Ghost): \(endpointString)")
        } else {
            endpointString = wireguard.peer.endpoint
            SharedLogger.log(.wireGuard, "Endpoint (standalone): \(endpointString)")
        }

        guard let endpoint = Endpoint(from: endpointString) else {
            SharedLogger.log(.wireGuard, "ERROR: Invalid endpoint: \(endpointString)")
            throw PacketTunnelProviderError.savedProtocolConfigurationIsInvalid
        }
        config.endpoint = endpoint

        if wireguard.peer.persistentKeepalive > 0 {
            config.persistentKeepAlive = UInt16(clamping: wireguard.peer.persistentKeepalive)
        }

        return config
    }
}
