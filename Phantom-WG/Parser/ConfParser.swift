import Foundation

/// Parses .conf format — [Wstunnel] (optional), [Interface], [Peer].
/// Follows WireGuardKit's key=value parse pattern.
/// Own parser because WireGuardKit is not available in the main app target.

enum ConfParser {

    enum ParseError: Error, LocalizedError {
        case emptyInput
        case noInterfaceSection
        case noPeerSection
        case missingKey(section: String, key: String)
        case invalidValue(section: String, key: String, detail: String)

        var errorDescription: String? {
            switch self {
            case .emptyInput:
                return "Configuration is empty"
            case .noInterfaceSection:
                return "Missing [Interface] section"
            case .noPeerSection:
                return "Missing [Peer] section"
            case .missingKey(let section, let key):
                return "[\(section)] missing required key: \(key)"
            case .invalidValue(let section, let key, let detail):
                return "[\(section)] invalid \(key): \(detail)"
            }
        }
    }

    /// Parses .conf string and returns TunnelConfig.
    /// Ghost mode if [Wstunnel] present, standalone WireGuard otherwise.
    /// Name is left empty — caller should set it before validation.
    static func parse(_ input: String) throws -> TunnelConfig {
        let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { throw ParseError.emptyInput }

        let sections = splitSections(trimmed)

        guard let interfaceAttrs = sections["interface"] else {
            throw ParseError.noInterfaceSection
        }
        guard let peerAttrs = sections["peer"] else {
            throw ParseError.noPeerSection
        }

        let wstunnel: WstunnelConfig?
        if let wsAttrs = sections["wstunnel"] {
            wstunnel = try parseWstunnel(wsAttrs)
        } else {
            wstunnel = nil
        }

        let iface = try parseInterface(interfaceAttrs)
        let peer = try parsePeer(peerAttrs)

        return TunnelConfig(
            name: "",
            wireguard: WireguardConfig(interface: iface, peer: peer),
            wstunnel: wstunnel
        )
    }

    // MARK: - Section Splitting

    /// Splits lines into sections — collects key=value pairs.
    /// Multi-entry keys (address, allowedips, dns) are joined with commas.
    private static func splitSections(_ input: String) -> [String: [String: String]] {
        let lines = input.components(separatedBy: .newlines)
        var result: [String: [String: String]] = [:]
        var currentSection: String?
        let multiEntryKeys: Set<String> = ["address", "allowedips", "dns"]

        for line in lines {
            let stripped = line.trimmingCharacters(in: .whitespaces)
            if stripped.isEmpty || stripped.hasPrefix("#") { continue }

            // Section header
            if stripped.hasPrefix("["), stripped.hasSuffix("]") {
                let name = String(stripped.dropFirst().dropLast()).lowercased()
                currentSection = name
                if result[name] == nil { result[name] = [:] }
                continue
            }

            // Key = Value
            guard let section = currentSection,
                  let equalsIndex = stripped.firstIndex(of: "=") else { continue }

            let key = stripped[..<equalsIndex].trimmingCharacters(in: .whitespaces).lowercased()
            let value = stripped[stripped.index(equalsIndex, offsetBy: 1)...]
                .trimmingCharacters(in: .whitespaces)

            if multiEntryKeys.contains(key), let existing = result[section]?[key] {
                result[section]?[key] = existing + ", " + value
            } else {
                result[section]?[key] = value
            }
        }

        return result
    }

    // MARK: - Wstunnel

    private static func parseWstunnel(_ attrs: [String: String]) throws -> WstunnelConfig {
        guard let url = attrs["url"], !url.isEmpty else {
            throw ParseError.missingKey(section: "Wstunnel", key: "Url")
        }
        guard let secret = attrs["secret"], !secret.isEmpty else {
            throw ParseError.missingKey(section: "Wstunnel", key: "Secret")
        }
        guard let tunnel = attrs["tunnel"], !tunnel.isEmpty else {
            throw ParseError.missingKey(section: "Wstunnel", key: "Tunnel")
        }

        // udp://127.0.0.1:51820:127.0.0.1:51820
        var raw = tunnel
        if raw.lowercased().hasPrefix("udp://") { raw = String(raw.dropFirst(6)) }

        let parts = raw.split(separator: ":", maxSplits: 3).map(String.init)
        guard parts.count == 4,
              let localPort = UInt16(parts[1]),
              let remotePort = UInt16(parts[3]) else {
            throw ParseError.invalidValue(
                section: "Wstunnel", key: "Tunnel",
                detail: "expected udp://host:port:host:port"
            )
        }

        return WstunnelConfig(
            url: url, secret: secret,
            localPort: localPort, remoteHost: parts[2], remotePort: remotePort
        )
    }

    // MARK: - Interface

    private static func parseInterface(_ attrs: [String: String]) throws -> InterfaceConfig {
        guard let privateKey = attrs["privatekey"], !privateKey.isEmpty else {
            throw ParseError.missingKey(section: "Interface", key: "PrivateKey")
        }
        guard let address = attrs["address"], !address.isEmpty else {
            throw ParseError.missingKey(section: "Interface", key: "Address")
        }

        return InterfaceConfig(
            privateKey: privateKey,
            address: address,
            dns: attrs["dns"] ?? "1.1.1.1, 9.9.9.9",
            mtu: Int(attrs["mtu"] ?? "1420") ?? 1420
        )
    }

    // MARK: - Peer

    private static func parsePeer(_ attrs: [String: String]) throws -> PeerConfig {
        guard let publicKey = attrs["publickey"], !publicKey.isEmpty else {
            throw ParseError.missingKey(section: "Peer", key: "PublicKey")
        }
        guard let endpoint = attrs["endpoint"], !endpoint.isEmpty else {
            throw ParseError.missingKey(section: "Peer", key: "Endpoint")
        }

        return PeerConfig(
            publicKey: publicKey,
            presharedKey: attrs["presharedkey"],
            allowedIPs: attrs["allowedips"] ?? "0.0.0.0/0, ::/0",
            endpoint: endpoint,
            persistentKeepalive: Int(attrs["persistentkeepalive"] ?? "25") ?? 25
        )
    }
}
