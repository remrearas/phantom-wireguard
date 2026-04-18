import SwiftUI
import AppKit

struct TunnelListView: View {
    @Environment(TunnelsManager.self) private var tunnelsManager
    @Environment(LocalizationManager.self) private var loc
    @Environment(SystemExtensionState.self) private var extensionState

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
            EmptyStateView(showingImport: $showingImport)
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
            SettingsMenu(
                showingUninstallConfirm: $showingUninstallConfirm,
                isUninstalling: uninstalling
            )
        }
        ToolbarItem(placement: .primaryAction) {
            Button {
                showingImport = true
            } label: {
                Image(systemName: "plus")
            }
            .accessibilityIdentifier(AXID.TunnelList.addButton)
        }
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
                // and PhantomApp swaps the root view to ExtensionGate's
                // DeactivatedView; no further work is needed here.
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
