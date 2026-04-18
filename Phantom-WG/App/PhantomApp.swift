import SwiftUI

@main
struct PhantomApp: App {
    @State private var tunnelsManager = TunnelsManagerLoader()
    @State private var loc = LocalizationManager.shared

    var body: some Scene {
        WindowGroup {
            Group {
                if let manager = tunnelsManager.manager {
                    TunnelListView()
                        .environment(manager)
                } else if let error = tunnelsManager.loadError {
                    ContentUnavailableView(
                        loc.t("error"),
                        systemImage: "exclamationmark.triangle",
                        description: Text(error)
                    )
                } else {
                    loadingView
                        .task { await tunnelsManager.load() }
                }
            }
            .environment(loc)
            .tint(Color.accentColor)
        }
    }

    private var loadingView: some View {
        VStack(spacing: 20) {
            Image("PhantomLogo")
                .resizable()
                .scaledToFit()
                .frame(width: 160, height: 160)
            ProgressView(loc.t("app_loading"))
                .tint(.secondary)
        }
    }
}
