import SwiftUI

// MARK: - Actions & Stats Polling

extension TunnelDetailView {

    func loadDraft() {
        if let config = tunnel.tunnelConfig {
            let next = TunnelDraft(from: config)
            draft = next
            originalDraft = next
            fieldErrors = [:]
        }
    }

    /// Commits the current draft via native form submit (Enter on a
    /// field). If the draft is unchanged or equal to the last committed
    /// snapshot, this is a no-op. If validation fails, field errors are
    /// surfaced inline and auto-dismiss after a short delay so the UI
    /// returns to the default state on its own. On success the typed
    /// config is pushed to the tunnel provider.
    func commitDraft() {
        guard isEditable, draft != originalDraft else { return }

        let result = draft.validate()

        // Local validation failed — revert the draft immediately so the
        // user sees the known-good value, then surface the errors for a
        // few seconds before the banner fades out.
        if !result.errors.isEmpty {
            rejectCommit(with: result.errors)
            return
        }

        guard let config = result.config else { return }

        Task {
            do {
                try await tunnelsManager.modify(tunnel: tunnel, with: config,
                                                onDemand: tunnel.activateOnDemandSetting)
                originalDraft = draft
            } catch TunnelManagementError.tunnelAlreadyExistsWithThatName {
                rejectCommit(with: [.name: .nameAlreadyExists])
            } catch TunnelManagementError.tunnelInvalidName {
                rejectCommit(with: [.name: .empty])
            } catch {
                // Genuine system-level failure (NE framework error,
                // saving preferences, etc.) — surface via modal alert
                // because it is not tied to any single form field.
                errorMessage = error.localizedDescription
                showingError = true
            }
        }
    }

    /// Rolls the draft back to the last committed snapshot and marks
    /// the offending fields with typed errors. The error banner is
    /// scheduled to fade out on its own; the draft itself has already
    /// returned to the known-good state.
    private func rejectCommit(
        with errors: [TunnelDraft.Field: FieldValidationError]
    ) {
        programmaticRevert = true
        draft = originalDraft
        fieldErrors = errors
        scheduleFieldErrorClear()
    }

    /// Removes the inline error banner after a short grace period so
    /// the form returns to a neutral appearance. The draft itself is
    /// untouched here — it has already been reverted at the moment of
    /// rejection, so the user always looks at a known-good value.
    private func scheduleFieldErrorClear() {
        fieldErrorClearTask?.cancel()
        fieldErrorClearTask = Task { @MainActor in
            do {
                try await Task.sleep(for: .seconds(3))
            } catch {
                return
            }
            withAnimation(.default) {
                fieldErrors = [:]
            }
            fieldErrorClearTask = nil
        }
    }

    // MARK: - Copy Actions

    func copyConf() {
        // Validate-before-copy so the output is always well-formed; if
        // validation fails we fall back to whatever the user has typed.
        let result = draft.validate()
        let contents = result.config?.asConfString() ?? draftToBestEffortConfString()
        UIPasteboard.general.string = contents
    }

    func copyLogs() {
        let text = logStore.entries.map { $0.text }.joined(separator: "\n")
        UIPasteboard.general.string = text.isEmpty ? loc.t("detail_no_logs") : text
    }

    /// Fallback serializer used when the draft has unresolved validation
    /// errors — emits whatever the user has typed so they can still copy
    /// partial work out for external inspection.
    private func draftToBestEffortConfString() -> String {
        var lines: [String] = []

        if let ws = draft.wstunnel {
            lines.append("[Wstunnel]")
            lines.append("Url = \(ws.url)")
            lines.append("Secret = \(ws.secret)")
            lines.append("Tunnel = udp://\(ws.localHost):\(ws.localPort):\(ws.remoteHost):\(ws.remotePort)")
            lines.append("")
        }

        lines.append("[Interface]")
        lines.append("PrivateKey = \(draft.wireguard.interface.privateKey)")
        lines.append("Address = \(draft.wireguard.interface.addresses)")
        lines.append("DNS = \(draft.wireguard.interface.dnsServers)")
        lines.append("MTU = \(draft.wireguard.interface.mtu)")
        lines.append("")

        lines.append("[Peer]")
        lines.append("PublicKey = \(draft.wireguard.peer.publicKey)")
        if !draft.wireguard.peer.presharedKey.isEmpty {
            lines.append("PresharedKey = \(draft.wireguard.peer.presharedKey)")
        }
        lines.append("AllowedIPs = \(draft.wireguard.peer.allowedIPs)")
        lines.append("Endpoint = \(draft.wireguard.peer.endpoint)")
        lines.append("PersistentKeepalive = \(draft.wireguard.peer.persistentKeepalive)")

        return lines.joined(separator: "\n")
    }

    // MARK: - Reset

    /// Ask the extension to restart its tunnel layer in place.
    /// No user confirmation: reset is soft — worst case the user
    /// sees a brief disconnect and presses it again. utun / routes
    /// are preserved across the cycle (no physical-interface leak).
    func resetConnection() {
        Task {
            do {
                try await tunnelsManager.resetConnection(of: tunnel)
            } catch {
                errorMessage = error.localizedDescription
                showingError = true
            }
        }
    }

    // MARK: - Delete

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

    // MARK: - On-Demand Binding

    var onDemandBinding: Binding<Bool> {
        Binding(
            get: { tunnel.isActivateOnDemandEnabled },
            set: { isOn in
                let option: ActivateOnDemandOption = isOn ? .wifiOrCellular : .off
                let provider = tunnel.tunnelProvider
                option.apply(on: provider)
                Task {
                    try? await provider.savePreferences()
                    try? await provider.loadPreferences()
                }
            }
        )
    }
}
