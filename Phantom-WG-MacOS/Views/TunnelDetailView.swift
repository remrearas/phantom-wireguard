import SwiftUI

struct TunnelDetailView: View {
    @ObservedObject var tunnel: TunnelContainer
    @StateObject private var logStore: LogStore
    @EnvironmentObject var tunnelsManager: TunnelsManager
    @EnvironmentObject var loc: LocalizationManager
    @Environment(\.dismiss) var dismiss

    @State var editConfig: TunnelConfig = .empty()
    @State var originalConfig: TunnelConfig = .empty()
    @State var showingDeleteConfirmation = false
    @State var errorMessage: String?
    @State var showingError = false
    @State var copiedItem: String?

    // Stats
    @State var lastHandshake: String = "—"
    @State var rxBytes: String = "—"
    @State var txBytes: String = "—"
    @State var statsPollingTask: Task<Void, Never>?

    /// Engine'den türetilen convenience — tüm field disabled/enabled kararları buradan
    private var isEditable: Bool { PhantomUIEngine.canEditConfig(status: tunnel.status) }

    init(tunnel: TunnelContainer) {
        self.tunnel = tunnel
        _logStore = StateObject(wrappedValue: LogStore(tunnel: tunnel))
    }

    var body: some View {
        List {
            statusSection
            statsSection
            nameSection
            if editConfig.isGhostMode { wstunnelSection }
            interfaceSection
            peerSection
            logSection
            actionsSection
        }
        .navigationTitle(editConfig.name.isEmpty ? loc.t("detail_tunnel") : editConfig.name)
        .onChange(of: editConfig) { _, newConfig in
            if PhantomUIEngine.shouldAutoSave(
                status: tunnel.status,
                hasChanges: newConfig != originalConfig
            ) {
                saveConfig()
            }
        }
        .onAppear {
            loadConfig()
            logStore.startPolling()
            if tunnel.status == .active { startStatsPolling() }
        }
        .onDisappear {
            logStore.stopPolling()
            stopStatsPolling()
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
        Section {
            HStack(spacing: 12) {
                ZStack {
                    RoundedRectangle(cornerRadius: 8)
                        .fill(PhantomUIEngine.statusColor(for: tunnel.status).opacity(0.12))
                        .frame(width: 36, height: 36)
                    Image(systemName: PhantomUIEngine.statusIcon(for: tunnel.status))
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(PhantomUIEngine.statusColor(for: tunnel.status))
                }

                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 6) {
                        Text(tunnel.status.localizedDescription)
                            .font(.body.weight(.medium))
                            .foregroundStyle(PhantomUIEngine.statusColor(for: tunnel.status))

                        Text(editConfig.isGhostMode ? "Ghost" : "WireGuard")
                            .font(.caption2.weight(.semibold))
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(
                                Capsule().fill(editConfig.isGhostMode ? Color.purple.opacity(0.15) : Color.blue.opacity(0.15))
                            )
                            .foregroundStyle(editConfig.isGhostMode ? .purple : .blue)
                    }
                    if let error = tunnel.lastActivationError {
                        Text(error.alertText)
                            .font(.caption)
                            .foregroundStyle(.red)
                    }
                }

                Spacer()

                Toggle("", isOn: PhantomUIEngine.tunnelToggleBinding(for: tunnel, manager: tunnelsManager))
                    .toggleStyle(.switch)
                    .labelsHidden()
                    .disabled(!PhantomUIEngine.canToggleTunnel(
                        tunnelStatus: tunnel.status,
                        allStatuses: tunnelsManager.tunnels.map(\.status)
                    ))
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
            PhantomTextField(label: loc.t("detail_name"), text: $editConfig.name, isDisabled: !isEditable)
        } header: {
            Label(loc.t("detail_general"), systemImage: "gearshape")
        }
    }

    @ViewBuilder
    private var wstunnelSection: some View {
        if editConfig.wstunnel != nil {
            Section {
                PhantomTextField(label: loc.t("detail_server_url"), text: wstunnelBinding(\.url), isDisabled: !isEditable)
                PhantomTextField(label: loc.t("detail_secret"), text: wstunnelBinding(\.secret), isDisabled: !isEditable)
                PhantomNumericField(label: loc.t("detail_local_port"), value: wstunnelPortBinding(\.localPort), isDisabled: !isEditable)
                PhantomTextField(label: loc.t("detail_remote_host"), text: wstunnelBinding(\.remoteHost), isDisabled: !isEditable)
                PhantomNumericField(label: loc.t("detail_remote_port"), value: wstunnelPortBinding(\.remotePort), isDisabled: !isEditable)
            } header: {
                Label(loc.t("detail_wstunnel"), systemImage: "network.badge.shield.half.filled")
            }
        }
    }

    private func wstunnelBinding(_ keyPath: WritableKeyPath<WstunnelConfig, String>) -> Binding<String> {
        Binding(
            get: { editConfig.wstunnel?[keyPath: keyPath] ?? "" },
            set: { editConfig.wstunnel?[keyPath: keyPath] = $0 }
        )
    }

    private func wstunnelPortBinding(_ keyPath: WritableKeyPath<WstunnelConfig, UInt16>) -> Binding<UInt16> {
        Binding(
            get: { editConfig.wstunnel?[keyPath: keyPath] ?? 0 },
            set: { editConfig.wstunnel?[keyPath: keyPath] = $0 }
        )
    }

    private var interfaceSection: some View {
        Section {
            PhantomTextField(label: loc.t("detail_private_key"), text: $editConfig.wireguard.interface.privateKey, isDisabled: !isEditable)
            PhantomTextField(label: loc.t("detail_address"), text: $editConfig.wireguard.interface.address, isDisabled: !isEditable)
            PhantomTextField(label: loc.t("detail_dns"), text: $editConfig.wireguard.interface.dns, isDisabled: !isEditable)
            PhantomNumericField(label: loc.t("detail_mtu"), value: $editConfig.wireguard.interface.mtu, isDisabled: !isEditable)
        } header: {
            Label(loc.t("detail_interface"), systemImage: "rectangle.connected.to.line.below")
        }
    }

    private var peerSection: some View {
        Section {
            PhantomTextField(label: loc.t("detail_public_key"), text: $editConfig.wireguard.peer.publicKey, isDisabled: !isEditable)
            PhantomTextField(label: loc.t("detail_preshared_key"), text: presharedKeyBinding, isDisabled: !isEditable)
            PhantomTextField(label: loc.t("detail_allowed_ips"), text: $editConfig.wireguard.peer.allowedIPs, isDisabled: !isEditable)
            PhantomTextField(label: loc.t("detail_endpoint"), text: $editConfig.wireguard.peer.endpoint, isDisabled: !isEditable)
            PhantomNumericField(
                label: loc.t("detail_keepalive"),
                value: $editConfig.wireguard.peer.persistentKeepalive,
                isDisabled: !isEditable
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
            .disabled(!PhantomUIEngine.canDeleteTunnel(status: tunnel.status))
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

    // MARK: - Bindings

    private var presharedKeyBinding: Binding<String> {
        Binding(
            get: { editConfig.wireguard.peer.presharedKey ?? "" },
            set: { editConfig.wireguard.peer.presharedKey = $0.isEmpty ? nil : $0 }
        )
    }

}
