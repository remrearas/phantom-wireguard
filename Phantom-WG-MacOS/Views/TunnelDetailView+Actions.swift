import SwiftUI

// MARK: - Actions & Stats Polling

extension TunnelDetailView {

    func loadConfig() {
        if let config = tunnel.tunnelConfig {
            editConfig = config
            originalConfig = config
        }
    }

    func saveConfig() {
        Task {
            do {
                try await tunnelsManager.modify(tunnel: tunnel, with: editConfig)
                originalConfig = editConfig
            } catch {
                errorMessage = error.localizedDescription
                showingError = true
            }
        }
    }

    func copyConf() {
        var lines: [String] = []

        if let ws = editConfig.wstunnel {
            lines.append("[Wstunnel]")
            lines.append("Url = \(ws.url)")
            lines.append("Secret = \(ws.secret)")
            lines.append("Tunnel = udp://127.0.0.1:\(ws.localPort):\(ws.remoteHost):\(ws.remotePort)")
            lines.append("")
        }

        lines.append("[Interface]")
        lines.append("PrivateKey = \(editConfig.wireguard.interface.privateKey)")
        lines.append("Address = \(editConfig.wireguard.interface.address)")
        lines.append("DNS = \(editConfig.wireguard.interface.dns)")
        lines.append("MTU = \(editConfig.wireguard.interface.mtu)")
        lines.append("")

        lines.append("[Peer]")
        lines.append("PublicKey = \(editConfig.wireguard.peer.publicKey)")
        if let psk = editConfig.wireguard.peer.presharedKey, !psk.isEmpty {
            lines.append("PresharedKey = \(psk)")
        }
        lines.append("AllowedIPs = \(editConfig.wireguard.peer.allowedIPs)")
        lines.append("Endpoint = \(editConfig.wireguard.peer.endpoint)")
        lines.append("PersistentKeepalive = \(editConfig.wireguard.peer.persistentKeepalive)")

        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(lines.joined(separator: "\n"), forType: .string)
    }

    func deleteTunnel() {
        if tunnel.status != .inactive {
            tunnelsManager.startDeactivation(of: tunnel)
        }
        Task {
            do {
                try await tunnelsManager.remove(tunnel: tunnel)
                dismiss()
            } catch {
                errorMessage = error.localizedDescription
                showingError = true
            }
        }
    }

    // MARK: - Stats Polling

    func startStatsPolling() {
        stopStatsPolling()
        pollStats()
        statsPollingTask = Task {
            while !Task.isCancelled {
                do {
                    try await Task.sleep(for: .seconds(1))
                } catch {
                    break
                }
                pollStats()
            }
        }
    }

    func stopStatsPolling() {
        statsPollingTask?.cancel()
        statsPollingTask = nil
    }

    func resetStats() {
        lastHandshake = "—"
        rxBytes = "—"
        txBytes = "—"
    }

    func pollStats() {
        guard tunnel.status == .active else { return }

        do {
            try tunnel.tunnelProvider.sendProviderMessage(Data([0])) { response in
                guard let data = response, let config = String(data: data, encoding: .utf8) else { return }
                Task { @MainActor in
                    applyRuntimeStats(config)
                }
            }
        } catch {
            // Session might not be ready yet
        }
    }

    func applyRuntimeStats(_ config: String) {
        let stats = StatsFormatter.parse(config)
        rxBytes = StatsFormatter.formatBytes(stats.rxBytes)
        txBytes = StatsFormatter.formatBytes(stats.txBytes)

        if stats.lastHandshakeTimestamp > 0 {
            let date = Date(timeIntervalSince1970: TimeInterval(stats.lastHandshakeTimestamp))
            let elapsed = Date().timeIntervalSince(date)
            lastHandshake = StatsFormatter.formatTimeAgo(elapsed, loc: loc)
        } else {
            lastHandshake = "—"
        }
    }
}
