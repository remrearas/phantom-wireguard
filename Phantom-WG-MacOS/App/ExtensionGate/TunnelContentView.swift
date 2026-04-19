import SwiftUI

/// Loading gate between successful system extension activation and
/// the actual tunnel list. Waits for the async preference load on
/// `TunnelsManagerLoader`, surfaces a dedicated error view if the
/// load fails, and otherwise hands control to `TunnelListView` with
/// the live manager in environment.
struct TunnelContentView: View {
    var loader: TunnelsManagerLoader
    @Environment(LocalizationManager.self) private var loc
    @Environment(SplitTunnelingStore.self) private var splitTunnelingStore

    var body: some View {
        Group {
            if let manager = loader.manager {
                TunnelListView()
                    .environment(manager)
                    .onAppear {
                        // Wire the store into the manager so activation
                        // runs reconcile before dispatch. The reference
                        // is weak on the manager side — no retain cycle.
                        manager.splitTunnelingStore = splitTunnelingStore
                    }
            } else if let error = loader.loadError {
                ContentUnavailableView(
                    loc.t("error"),
                    systemImage: "exclamationmark.triangle",
                    description: Text(error)
                )
                .accessibilityElement(children: .combine)
                .accessibilityIdentifier(AXID.ExtensionGate.tunnelLoadError)
            } else {
                VStack(spacing: 20) {
                    Image("PhantomLogo")
                        .resizable()
                        .scaledToFit()
                        .frame(width: 160, height: 160)
                    ProgressView(loc.t("app_loading"))
                        .tint(.secondary)
                }
                .task { await loader.load() }
            }
        }
    }
}
