import SwiftUI

struct TunnelListView: View {
    @Environment(TunnelsManager.self) private var tunnelsManager
    @Environment(LocalizationManager.self) private var loc
    @State private var showingImport = false
    @State private var errorMessage: String?
    @State private var showingError = false

    var body: some View {
        NavigationStack {
            Group {
                if tunnelsManager.tunnels.isEmpty {
                    EmptyStateView(showingImport: $showingImport)
                } else {
                    List {
                        ForEach(tunnelsManager.tunnels) { tunnel in
                            NavigationLink(destination: TunnelDetailView(tunnel: tunnel)) {
                                TunnelRow(tunnel: tunnel)
                            }
                        }
                        .onDelete { offsets in deleteTunnels(at: offsets) }

                        aboutSection
                    }
                }
            }
            .navigationTitle(loc.t("app_title"))
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    LanguageToggleButton()
                }

                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showingImport = true
                    } label: {
                        Image(systemName: "plus")
                    }
                    .accessibilityIdentifier(AXID.TunnelList.addButton)
                }
            }
            .sheet(isPresented: $showingImport) {
                TunnelImportView()
            }
            .alert(loc.t("error"), isPresented: $showingError) {
                Button(loc.t("ok")) {}
                    .accessibilityIdentifier(AXID.TunnelList.errorAlertOK)
            } message: {
                Text(errorMessage ?? "")
            }
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

    private func deleteTunnels(at offsets: IndexSet) {
        let tunnelsToDelete = offsets.map { tunnelsManager.tunnels[$0] }
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
