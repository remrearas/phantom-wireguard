import Foundation

// MARK: - Tunnels Manager Loader

@MainActor
class TunnelsManagerLoader: ObservableObject {
    @Published var manager: TunnelsManager?
    @Published var loadError: String?

    func load() async {
        do {
            manager = try await TunnelsManager.create()
        } catch {
            loadError = error.localizedDescription
        }
    }
}
