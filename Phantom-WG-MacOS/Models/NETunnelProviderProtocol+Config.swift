import NetworkExtension

extension NETunnelProviderProtocol {

    /// Read config from providerConfiguration (two separate JSON blobs).
    var tunnelConfig: TunnelConfig? {
        guard let configId = providerConfiguration?["configId"] as? String,
              let id = UUID(uuidString: configId),
              let name = providerConfiguration?["name"] as? String,
              let wgData = providerConfiguration?["wireguardConfig"] as? Data,
              let wireguard = try? JSONDecoder().decode(WireguardConfig.self, from: wgData) else {
            return nil
        }

        var wstunnel: WstunnelConfig?
        if let wsData = providerConfiguration?["wstunnelConfig"] as? Data {
            wstunnel = try? JSONDecoder().decode(WstunnelConfig.self, from: wsData)
        }

        return TunnelConfig(id: id, name: name, wireguard: wireguard, wstunnel: wstunnel)
    }

    /// Create protocol with config embedded in providerConfiguration.
    convenience init?(tunnelConfig config: TunnelConfig,
                      previouslyFrom proto: NETunnelProviderProtocol? = nil) {
        self.init()

        guard let wgData = try? JSONEncoder().encode(config.wireguard) else { return nil }

        providerBundleIdentifier = "com.remrearas.Phantom-WG-MacOS.PhantomTunnel"

        var providerConfig: [String: Any] = [
            "configId": config.id.uuidString,
            "name": config.name,
            "wireguardConfig": wgData
        ]

        if let wstunnel = config.wstunnel,
           let wsData = try? JSONEncoder().encode(wstunnel) {
            providerConfig["wstunnelConfig"] = wsData
        }

        providerConfiguration = providerConfig
        serverAddress = config.wstunnel?.url ?? config.wireguard.peer.endpoint
    }
}
