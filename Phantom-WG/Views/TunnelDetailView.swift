import SwiftUI

/// Tunnel detail + editor. Orchestrates the draft/original/errors
/// state machine — edits are staged in a `TunnelDraft`, committed via
/// native form submit (Enter on any field), and either persisted or
/// reverted with inline per-field errors. Ghost-mode wstunnel section
/// appears only when the typed config carries a wstunnel block.
struct TunnelDetailView: View {
    @ObservedObject var tunnel: TunnelContainer
    @StateObject private var logStore: LogStore
    @EnvironmentObject var tunnelsManager: TunnelsManager
    @EnvironmentObject var loc: LocalizationManager
    @Environment(\.dismiss) private var dismiss

    @State private var draft: TunnelDraft = .empty()
    @State private var originalDraft: TunnelDraft = .empty()
    @State private var fieldErrors: [TunnelDraft.Field: FieldValidationError] = [:]
    @State private var fieldErrorClearTask: Task<Void, Never>?
    /// Distinguishes a programmatic revert (rejection of an invalid
    /// commit) from a user edit. Set to `true` just before reverting
    /// the draft; the next `onChange(of: draft)` consumes and resets it.
    @State private var programmaticRevert: Bool = false
    @State private var showingDeleteConfirmation = false
    @State private var errorMessage: String?
    @State private var showingError = false
    @State private var copiedItem: String?

    // Stats
    @State private var lastHandshake: String = "—"
    @State private var rxBytes: String = "—"
    @State private var txBytes: String = "—"
    @State private var statsPollingTask: Task<Void, Never>?

    /// Config fields are only editable while the tunnel is inactive.
    private var isEditable: Bool { tunnel.status == .inactive }

    init(tunnel: TunnelContainer) {
        self.tunnel = tunnel
        _logStore = StateObject(wrappedValue: LogStore(tunnelId: tunnel.tunnelConfig?.id.uuidString))
    }

    var body: some View {
        List {
            statusSection
            statsSection
            onDemandSection
            nameSection
            if let wstunnelBinding = Binding($draft.wstunnel) {
                wstunnelSection(draft: wstunnelBinding)
            }
            interfaceSection
            peerSection
            logSection
            actionsSection
        }
        .navigationTitle(draft.name.isEmpty ? loc.t("detail_tunnel") : draft.name)
        .navigationBarTitleDisplayMode(.inline)
        .onChange(of: draft) { _, _ in
            // Skip the clearing side-effect when the change originated
            // from a programmatic revert (invalid commit rollback) so
            // the accompanying error banner can still be seen.
            if programmaticRevert {
                programmaticRevert = false
                return
            }
            // User edit: drop stale errors and cancel the auto-dismiss
            // timer — the next commit re-validates the full draft.
            if !fieldErrors.isEmpty {
                fieldErrors = [:]
                fieldErrorClearTask?.cancel()
                fieldErrorClearTask = nil
            }
        }
        .onSubmit {
            // Native form commit: when any field's Enter fires, validate
            // the draft and persist if it's clean. Invalid fields show
            // their errors inline; the draft itself remains editable.
            commitDraft()
        }
        .onAppear {
            loadDraft()
            logStore.startPolling()
            if tunnel.status == .active { startStatsPolling() }
        }
        .onDisappear {
            logStore.stopPolling()
            stopStatsPolling()
            fieldErrorClearTask?.cancel()
            fieldErrorClearTask = nil
        }
        .confirmationDialog(loc.t("detail_delete_confirm_title"),
                            isPresented: $showingDeleteConfirmation,
                            titleVisibility: .visible) {
            Button(loc.t("delete"), role: .destructive) { deleteTunnel() }
            Button(loc.t("cancel"), role: .cancel) {}
        } message: {
            Text(loc.t("detail_delete_confirm_message"))
        }
        .alert(loc.t("error"), isPresented: $showingError) {
            Button(loc.t("ok")) {}
        } message: {
            Text(errorMessage ?? "")
        }
        .onChange(of: tunnel.status) { _, newStatus in
            if newStatus == .active {
                startStatsPolling()
            } else if newStatus == .inactive {
                stopStatsPolling()
                resetStats()
            }
        }
    }

    // MARK: - Sections

    private var statusSection: some View {
        let color = tunnel.status.color
        return Section {
            HStack(spacing: 12) {
                ZStack {
                    RoundedRectangle(cornerRadius: 8)
                        .fill(color.opacity(0.12))
                        .frame(width: 36, height: 36)
                    Image(systemName: tunnel.status.iconName)
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(color)
                }

                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 6) {
                        Text(tunnel.status.localizedDescription)
                            .font(.body.weight(.medium))
                            .foregroundStyle(color)

                        Text(draft.wstunnel != nil ? "Ghost" : "WireGuard")
                            .font(.caption2.weight(.semibold))
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(
                                Capsule().fill((draft.wstunnel != nil) ? Color.purple.opacity(0.15) : Color.blue.opacity(0.15))
                            )
                            .foregroundStyle((draft.wstunnel != nil) ? .purple : .blue)
                    }
                    if let error = tunnel.lastActivationError {
                        Text(error.alertText)
                            .font(.caption)
                            .foregroundStyle(.red)
                    }
                }

                Spacer()

                Toggle("", isOn: tunnel.toggleBinding(manager: tunnelsManager))
                    .labelsHidden()
            }
        } header: {
            Label(loc.t("detail_status"), systemImage: "antenna.radiowaves.left.and.right")
        }
    }

    private var statsSection: some View {
        Section {
            StatRow(icon: "hand.wave", label: loc.t("detail_handshake"), value: lastHandshake)
            StatRow(icon: "arrow.down.circle", label: loc.t("detail_received"), value: rxBytes, valueColor: .green)
            StatRow(icon: "arrow.up.circle", label: loc.t("detail_sent"), value: txBytes, valueColor: .blue)
        } header: {
            Label(loc.t("detail_transfer"), systemImage: "chart.bar.fill")
        }
    }

    private var onDemandSection: some View {
        Section {
            Toggle(isOn: onDemandBinding) {
                Label(loc.t("detail_on_demand"), systemImage: "bolt.shield")
            }
        } footer: {
            Text(loc.t("detail_on_demand_footer"))
        }
    }

    private var nameSection: some View {
        Section {
            PhantomTextField(
                label: loc.t("detail_name"),
                text: $draft.name,
                isDisabled: !isEditable,
                errorMessage: message(for: .name)
            )
        } header: {
            Label(loc.t("detail_general"), systemImage: "gearshape")
        }
    }

    private func wstunnelSection(draft: Binding<WstunnelDraft>) -> some View {
        Section {
            PhantomTextField(
                label: loc.t("detail_server_url"),
                text: draft.url,
                isDisabled: !isEditable,
                errorMessage: message(for: .wstunnelUrl)
            )
            PhantomTextField(
                label: loc.t("detail_secret"),
                text: draft.secret,
                isDisabled: !isEditable,
                errorMessage: message(for: .wstunnelSecret)
            )
            PhantomTextField(
                label: loc.t("detail_local_host"),
                text: draft.localHost,
                isDisabled: !isEditable,
                errorMessage: message(for: .wstunnelLocalHost)
            )
            PhantomStringNumericField(
                label: loc.t("detail_local_port"),
                text: draft.localPort,
                isDisabled: !isEditable,
                errorMessage: message(for: .wstunnelLocalPort)
            )
            PhantomTextField(
                label: loc.t("detail_remote_host"),
                text: draft.remoteHost,
                isDisabled: !isEditable,
                errorMessage: message(for: .wstunnelRemoteHost)
            )
            PhantomStringNumericField(
                label: loc.t("detail_remote_port"),
                text: draft.remotePort,
                isDisabled: !isEditable,
                errorMessage: message(for: .wstunnelRemotePort)
            )
        } header: {
            Label(loc.t("detail_wstunnel"), systemImage: "network.badge.shield.half.filled")
        }
    }

    private var interfaceSection: some View {
        Section {
            PhantomTextField(
                label: loc.t("detail_private_key"),
                text: $draft.wireguard.interface.privateKey,
                isDisabled: !isEditable,
                errorMessage: message(for: .interfacePrivateKey)
            )
            PhantomTextField(
                label: loc.t("detail_address"),
                text: $draft.wireguard.interface.addresses,
                isDisabled: !isEditable,
                errorMessage: message(for: .interfaceAddresses)
            )
            PhantomTextField(
                label: loc.t("detail_dns"),
                text: $draft.wireguard.interface.dnsServers,
                isDisabled: !isEditable,
                errorMessage: message(for: .interfaceDnsServers)
            )
            PhantomStringNumericField(
                label: loc.t("detail_mtu"),
                text: $draft.wireguard.interface.mtu,
                isDisabled: !isEditable,
                errorMessage: message(for: .interfaceMTU)
            )
        } header: {
            Label(loc.t("detail_interface"), systemImage: "rectangle.connected.to.line.below")
        }
    }

    private var peerSection: some View {
        Section {
            PhantomTextField(
                label: loc.t("detail_public_key"),
                text: $draft.wireguard.peer.publicKey,
                isDisabled: !isEditable,
                errorMessage: message(for: .peerPublicKey)
            )
            PhantomTextField(
                label: loc.t("detail_preshared_key"),
                text: $draft.wireguard.peer.presharedKey,
                isDisabled: !isEditable,
                errorMessage: message(for: .peerPresharedKey)
            )
            PhantomTextField(
                label: loc.t("detail_allowed_ips"),
                text: $draft.wireguard.peer.allowedIPs,
                isDisabled: !isEditable,
                errorMessage: message(for: .peerAllowedIPs)
            )
            PhantomTextField(
                label: loc.t("detail_endpoint"),
                text: $draft.wireguard.peer.endpoint,
                isDisabled: !isEditable,
                errorMessage: message(for: .peerEndpoint)
            )
            PhantomStringNumericField(
                label: loc.t("detail_keepalive"),
                text: $draft.wireguard.peer.persistentKeepalive,
                isDisabled: !isEditable,
                errorMessage: message(for: .peerPersistentKeepalive)
            )
        } header: {
            Label(loc.t("detail_peer"), systemImage: "point.3.connected.trianglepath.dotted")
        }
    }

    private var logSection: some View {
        Section {
            NavigationLink {
                LogView(logStore: logStore)
            } label: {
                HStack {
                    Label(loc.t("detail_logs"), systemImage: "text.justify.left")
                    Spacer()
                    Text("\(logStore.entries.count)")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                        .background(
                            Capsule()
                                .fill(Color(.systemGray5))
                        )
                }
            }
        }
    }

    private var actionsSection: some View {
        Section {
            copyButton(loc.t("detail_copy_conf"), icon: "doc.plaintext", id: "conf") { copyConf() }
            copyButton(loc.t("detail_copy_logs"), icon: "text.quote", id: "logs") { copyLogs() }

            Button {
                logStore.clear()
            } label: {
                Label(loc.t("detail_clear_logs"), systemImage: "trash.circle")
            }

            Button(role: .destructive) {
                showingDeleteConfirmation = true
            } label: {
                Label(loc.t("detail_delete_tunnel"), systemImage: "trash")
            }
            .disabled(tunnel.status != .inactive)
        } header: {
            Label(loc.t("detail_actions"), systemImage: "ellipsis.circle")
        }
    }

    // MARK: - Error Lookup

    private func message(for field: TunnelDraft.Field) -> String? {
        fieldErrors[field]?.localizedMessage(loc)
    }

    // MARK: - Copy Button

    private func copyButton(_ title: String, icon: String, id: String, action: @escaping () -> Void) -> some View {
        Button {
            action()
            copiedItem = id
            Task {
                try? await Task.sleep(for: .seconds(2))
                if copiedItem == id { copiedItem = nil }
            }
        } label: {
            Label(copiedItem == id ? loc.t("detail_copied") : title,
                  systemImage: copiedItem == id ? "checkmark.circle.fill" : icon)
            .foregroundStyle(copiedItem == id ? .green : .accentColor)
        }
    }

    // MARK: - On-Demand Binding

    private var onDemandBinding: Binding<Bool> {
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

    // MARK: - Draft Lifecycle

    private func loadDraft() {
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
    private func commitDraft() {
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

    private func copyConf() {
        // Validate-before-copy so the output is always well-formed; if
        // validation fails we fall back to whatever the user has typed.
        let result = draft.validate()
        let contents = result.config?.asConfString() ?? draftToBestEffortConfString()
        UIPasteboard.general.string = contents
    }

    private func copyLogs() {
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

    // MARK: - Delete

    private func deleteTunnel() {
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

    private func startStatsPolling() {
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

    private func stopStatsPolling() {
        statsPollingTask?.cancel()
        statsPollingTask = nil
    }

    private func resetStats() {
        lastHandshake = "—"
        rxBytes = "—"
        txBytes = "—"
    }

    private func pollStats() {
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

    private func applyRuntimeStats(_ config: String) {
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
