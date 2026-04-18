import SwiftUI

/// Tunnel detail + editor. The user can toggle activation, read live
/// stats, browse logs, and edit every configuration field. Edits are
/// staged in a `TunnelDraft`; the explicit Save button validates the
/// draft and applies the typed `TunnelConfig` to storage. Field-level
/// errors highlight offending inputs inline.
struct TunnelDetailView: View {
    @ObservedObject var tunnel: TunnelContainer
    @StateObject private var logStore: LogStore
    @EnvironmentObject var tunnelsManager: TunnelsManager
    @EnvironmentObject var loc: LocalizationManager
    @Environment(\.dismiss) var dismiss

    @State var draft: TunnelDraft = .empty()
    @State var originalDraft: TunnelDraft = .empty()
    @State var fieldErrors: [TunnelDraft.Field: FieldValidationError] = [:]
    @State var fieldErrorClearTask: Task<Void, Never>?
    /// Distinguishes a programmatic revert (rejection of an invalid
    /// commit) from a user edit. Set to `true` just before reverting
    /// the draft; the next `onChange(of: draft)` consumes and resets it.
    @State var programmaticRevert: Bool = false
    @State var showingDeleteConfirmation = false
    @State var errorMessage: String?
    @State var showingError = false
    @State var copiedItem: String?

    // Stats
    @State var lastHandshake: String = "—"
    @State var rxBytes: String = "—"
    @State var txBytes: String = "—"
    @State var statsPollingTask: Task<Void, Never>?

    /// Config fields are only editable while the tunnel is inactive.
    private var isEditable: Bool { tunnel.status == .inactive }

    init(tunnel: TunnelContainer) {
        self.tunnel = tunnel
        _logStore = StateObject(wrappedValue: LogStore(tunnel: tunnel))
    }

    var body: some View {
        List {
            statusSection
            statsSection
            nameSection
            if draft.wstunnel != nil { wstunnelSection }
            interfaceSection
            peerSection
            logSection
            actionsSection
        }
        .navigationTitle(draft.name.isEmpty ? loc.t("detail_tunnel") : draft.name)
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
                    .toggleStyle(.switch)
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

    @ViewBuilder
    private var wstunnelSection: some View {
        if let wstunnelBinding = Binding($draft.wstunnel) {
            Section {
                PhantomTextField(
                    label: loc.t("detail_server_url"),
                    text: wstunnelBinding.url,
                    isDisabled: !isEditable,
                    errorMessage: message(for: .wstunnelUrl)
                )
                PhantomTextField(
                    label: loc.t("detail_secret"),
                    text: wstunnelBinding.secret,
                    isDisabled: !isEditable,
                    errorMessage: message(for: .wstunnelSecret)
                )
                PhantomTextField(
                    label: loc.t("detail_local_host"),
                    text: wstunnelBinding.localHost,
                    isDisabled: !isEditable,
                    errorMessage: message(for: .wstunnelLocalHost)
                )
                PhantomStringNumericField(
                    label: loc.t("detail_local_port"),
                    text: wstunnelBinding.localPort,
                    isDisabled: !isEditable,
                    errorMessage: message(for: .wstunnelLocalPort)
                )
                PhantomTextField(
                    label: loc.t("detail_remote_host"),
                    text: wstunnelBinding.remoteHost,
                    isDisabled: !isEditable,
                    errorMessage: message(for: .wstunnelRemoteHost)
                )
                PhantomStringNumericField(
                    label: loc.t("detail_remote_port"),
                    text: wstunnelBinding.remotePort,
                    isDisabled: !isEditable,
                    errorMessage: message(for: .wstunnelRemotePort)
                )
            } header: {
                Label(loc.t("detail_wstunnel"), systemImage: "network.badge.shield.half.filled")
            }
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
                                .fill(Color.secondary.opacity(0.15))
                        )
                }
            }
            .listRowSeparator(.hidden)
        }
    }

    private var actionsSection: some View {
        Section {
            copyButton(loc.t("detail_copy_conf"), icon: "doc.text", id: "conf") { copyConf() }
                .listRowSeparator(.hidden)

            Button(role: .destructive) {
                showingDeleteConfirmation = true
            } label: {
                Label(loc.t("detail_delete_tunnel"), systemImage: "trash")
            }
            .disabled(tunnel.status != .inactive)
            .listRowSeparator(.hidden)
        } header: {
            Label(loc.t("detail_actions"), systemImage: "ellipsis.circle")
        }
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

    // MARK: - Error Lookup

    private func message(for field: TunnelDraft.Field) -> String? {
        fieldErrors[field]?.localizedMessage(loc)
    }
}
