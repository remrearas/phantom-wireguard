import SwiftUI
import AppKit

struct TunnelListView: View {
    @EnvironmentObject var tunnelsManager: TunnelsManager
    @EnvironmentObject var loc: LocalizationManager
    @EnvironmentObject var extensionState: SystemExtensionState
    @State private var showingImport = false
    @State private var errorMessage: String?
    @State private var showingError = false

    @State private var showingUninstallConfirm = false
    @State private var uninstalling = false

    /// Display order: non-inactive tunnels pinned to the top (preserves
    /// their mutual order — already newest-first via `TunnelsManager`);
    /// inactive tunnels follow in the same newest-first order. When a
    /// tunnel transitions back to inactive it slots into its natural
    /// `createdAt`-based position in the lower group.
    private var displayTunnels: [TunnelContainer] {
        let active = tunnelsManager.tunnels.filter { $0.status != .inactive }
        let inactive = tunnelsManager.tunnels.filter { $0.status == .inactive }
        return active + inactive
    }

    var body: some View {
        NavigationStack {
            listContent
                .navigationTitle(loc.t("app_title"))
                .toolbar { toolbarContent }
                .navigationDestination(isPresented: $showingImport) {
                    TunnelImportView()
                }
                .modifier(UninstallAlerts(
                    loc: loc,
                    errorMessage: $errorMessage,
                    showingError: $showingError,
                    showingUninstallConfirm: $showingUninstallConfirm,
                    onConfirm: runUninstall
                ))
                .disabled(uninstalling)
        }
    }

    @ViewBuilder
    private var listContent: some View {
        if tunnelsManager.tunnels.isEmpty {
            emptyState
        } else {
            List {
                ForEach(displayTunnels) { tunnel in
                    NavigationLink(destination: TunnelDetailView(tunnel: tunnel)) {
                        TunnelRow(tunnel: tunnel)
                    }
                }
                .onDelete { offsets in deleteTunnels(at: offsets) }

                aboutSection
            }
            .listStyle(.inset)
        }
    }

    @ToolbarContentBuilder
    private var toolbarContent: some ToolbarContent {
        ToolbarItem(placement: .navigation) {
            settingsMenu
        }
        ToolbarItem(placement: .primaryAction) {
            Button {
                showingImport = true
            } label: {
                Image(systemName: "plus")
            }
        }
    }

    // MARK: - Settings Menu

    private var settingsMenu: some View {
        Menu {
            Menu {
                Button {
                    loc.current = .en
                } label: {
                    languageRow(language: .en, isSelected: loc.current == .en)
                }
                Button {
                    loc.current = .tr
                } label: {
                    languageRow(language: .tr, isSelected: loc.current == .tr)
                }
            } label: {
                Label(loc.t("settings_language"), systemImage: "globe.badge.chevron.backward")
            }

            Divider()

            Link(destination: URL(string: "https://www.phantom.tc/docs")!) {
                Label(loc.t("documentation"), systemImage: "book")
            }
            Link(destination: URL(string: "https://www.phantom.tc")!) {
                Label(loc.t("website"), systemImage: "globe")
            }

            Divider()

            Button(role: .destructive) {
                showingUninstallConfirm = true
            } label: {
                Label(loc.t("settings_uninstall"), systemImage: "trash")
            }
            .disabled(uninstalling)
        } label: {
            Image(systemName: "gearshape")
        }
    }

    @ViewBuilder
    private func languageRow(language: LocalizationManager.Language, isSelected: Bool) -> some View {
        if isSelected {
            Label("\(language.flag) \(language.displayName)", systemImage: "checkmark")
        } else {
            Text("\(language.flag) \(language.displayName)")
        }
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 24) {
            Spacer()

            Image("PhantomLogo")
                .resizable()
                .scaledToFit()
                .frame(width: 100, height: 100)
                .opacity(0.35)

            VStack(spacing: 8) {
                Text(loc.t("tunnel_list_empty_title"))
                    .font(.title3)
                    .fontWeight(.semibold)
                Text(loc.t("tunnel_list_empty_description"))
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }

            Button {
                showingImport = true
            } label: {
                Label(loc.t("import_title"), systemImage: "plus.circle.fill")
                    .font(.body.weight(.medium))
                    .padding(.horizontal, 24)
                    .padding(.vertical, 12)
            }
            .buttonStyle(.borderedProminent)
            .buttonBorderShape(.capsule)

            Spacer()

            HStack(spacing: 24) {
                Link(destination: URL(string: "https://www.phantom.tc")!) {
                    Label(loc.t("website"), systemImage: "globe")
                        .font(.footnote)
                }
                Link(destination: URL(string: "https://www.phantom.tc/docs")!) {
                    Label(loc.t("documentation"), systemImage: "book")
                        .font(.footnote)
                }
            }
            .foregroundStyle(.secondary)
            .padding(.bottom, 20)
        }
        .padding()
    }

    private var aboutSection: some View {
        Section {
            Link(destination: URL(string: "https://www.phantom.tc")!) {
                Label(loc.t("website"), systemImage: "globe")
            }
            Link(destination: URL(string: "https://www.phantom.tc/docs")!) {
                Label(loc.t("documentation"), systemImage: "book")
            }
        }
    }

    // MARK: - Uninstall

    private func runUninstall() {
        uninstalling = true
        Task {
            do {
                try await tunnelsManager.removeAll()
                try await extensionState.deactivate()
                uninstalling = false
                // On success, extensionState.status transitions to .deactivated
                // and PhantomApp swaps the root view to extensionDeactivatedView;
                // no further work is needed here.
            } catch {
                uninstalling = false
                errorMessage = error.localizedDescription
                showingError = true
            }
        }
    }

    private func deleteTunnels(at offsets: IndexSet) {
        let visible = displayTunnels
        let tunnelsToDelete = offsets.map { visible[$0] }
        for tunnel in tunnelsToDelete {
            if tunnel.status != .inactive {
                tunnelsManager.startDeactivation(of: tunnel)
            }
            Task {
                do {
                    try await tunnelsManager.remove(tunnel: tunnel)
                } catch {
                    errorMessage = error.localizedDescription
                    showingError = true
                }
            }
        }
    }
}

// MARK: - Uninstall Alerts

private struct UninstallAlerts: ViewModifier {
    let loc: LocalizationManager
    @Binding var errorMessage: String?
    @Binding var showingError: Bool
    @Binding var showingUninstallConfirm: Bool
    let onConfirm: () -> Void

    func body(content: Content) -> some View {
        content
            .alert(loc.t("error"), isPresented: $showingError) {
                Button(loc.t("ok")) {}
            } message: {
                Text(errorMessage ?? "")
            }
            .alert(loc.t("uninstall_confirm_title"), isPresented: $showingUninstallConfirm) {
                Button(loc.t("cancel"), role: .cancel) {}
                Button(loc.t("uninstall_confirm_action"), role: .destructive) {
                    onConfirm()
                }
            } message: {
                Text(loc.t("uninstall_confirm_message"))
            }
    }
}

// MARK: - Tunnel Row

struct TunnelRow: View {
    @ObservedObject var tunnel: TunnelContainer
    @EnvironmentObject var tunnelsManager: TunnelsManager
    @EnvironmentObject var loc: LocalizationManager

    var body: some View {
        HStack(spacing: 12) {
            statusIndicator

            VStack(alignment: .leading, spacing: 3) {
                Text(tunnel.name)
                    .font(.body.weight(.medium))
                Text(tunnel.status.localizedDescription)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Toggle("", isOn: tunnel.toggleBinding(manager: tunnelsManager))
                .toggleStyle(.switch)
                .labelsHidden()
        }
        .padding(.vertical, 2)
    }

    private var statusIndicator: some View {
        let color = tunnel.status.color
        return ZStack {
            Circle()
                .fill(color.opacity(0.15))
                .frame(width: 32, height: 32)
            Image(systemName: tunnel.status.iconName)
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(color)
        }
    }
}
