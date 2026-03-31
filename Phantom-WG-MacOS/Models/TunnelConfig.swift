import Foundation

// MARK: - Tunnel Config (top-level, not Codable — stored as separate JSON blobs)

struct TunnelConfig: Identifiable, Equatable {
    var id: UUID
    var name: String
    var wireguard: WireguardConfig
    var wstunnel: WstunnelConfig?

    /// Ghost mode when wstunnel is present, standalone WireGuard otherwise.
    var isGhostMode: Bool { wstunnel != nil }

    init(id: UUID = UUID(), name: String, wireguard: WireguardConfig, wstunnel: WstunnelConfig? = nil) {
        self.id = id
        self.name = name
        self.wireguard = wireguard
        self.wstunnel = wstunnel
    }

    // MARK: - Validation

    enum ValidationError: Error, LocalizedError {
        case emptyName
        case emptyWstunnelUrl
        case emptyPrivateKey
        case emptyPublicKey
        case emptyAddress
        case emptyEndpoint

        var errorDescription: String? {
            switch self {
            case .emptyName:        return "Configuration name is required."
            case .emptyWstunnelUrl: return "Wstunnel server URL is required."
            case .emptyPrivateKey:  return "Interface private key is required."
            case .emptyPublicKey:   return "Peer public key is required."
            case .emptyAddress:     return "Interface address is required."
            case .emptyEndpoint:    return "Peer endpoint is required."
            }
        }
    }

    func validated() throws -> TunnelConfig {
        if name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            throw ValidationError.emptyName
        }
        if let ws = wstunnel, ws.url.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            throw ValidationError.emptyWstunnelUrl
        }
        if wireguard.interface.privateKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            throw ValidationError.emptyPrivateKey
        }
        if wireguard.interface.address.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            throw ValidationError.emptyAddress
        }
        if wireguard.peer.publicKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            throw ValidationError.emptyPublicKey
        }
        if wireguard.peer.endpoint.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            throw ValidationError.emptyEndpoint
        }
        return self
    }

    static func empty() -> TunnelConfig {
        TunnelConfig(
            name: "",
            wireguard: WireguardConfig(
                interface: InterfaceConfig(privateKey: "", address: "", dns: "1.1.1.1, 9.9.9.9", mtu: 1280),
                peer: PeerConfig(publicKey: "", allowedIPs: "0.0.0.0/0, ::/0", endpoint: "", persistentKeepalive: 25)
            )
        )
    }
}

// MARK: - WireGuard Config (IPC payload — encoded as JSON for storage and extension delivery)

struct WireguardConfig: Codable, Equatable {
    var interface: InterfaceConfig
    var peer: PeerConfig
}

struct InterfaceConfig: Codable, Equatable {
    var privateKey: String
    var address: String
    var dns: String
    var mtu: Int

    enum CodingKeys: String, CodingKey {
        case privateKey = "private_key"
        case address, dns, mtu
    }
}

struct PeerConfig: Codable, Equatable {
    var publicKey: String
    var presharedKey: String?
    var allowedIPs: String
    var endpoint: String
    var persistentKeepalive: Int

    enum CodingKeys: String, CodingKey {
        case publicKey = "public_key"
        case presharedKey = "preshared_key"
        case allowedIPs = "allowed_ips"
        case endpoint
        case persistentKeepalive = "persistent_keepalive"
    }
}

// MARK: - Wstunnel Config (encoded as JSON for storage and extension delivery)

struct WstunnelConfig: Codable, Equatable {
    var url: String
    var secret: String
    var localPort: UInt16
    var remoteHost: String
    var remotePort: UInt16

    enum CodingKeys: String, CodingKey {
        case url, secret
        case localPort = "local_port"
        case remoteHost = "remote_host"
        case remotePort = "remote_port"
    }
}
