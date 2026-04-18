import Foundation

// MARK: - Tunnels Manager Loader

/// Wrapper to hold TunnelsManager creation state, since TunnelsManager
/// requires async factory and can't be a direct @State at app launch.
@Observable
@MainActor
class TunnelsManagerLoader {
    var manager: TunnelsManager?
    var loadError: String?

    func load() async {
        do {
            manager = try await TunnelsManager.create()
        } catch {
            loadError = error.localizedDescription
        }
    }
}
