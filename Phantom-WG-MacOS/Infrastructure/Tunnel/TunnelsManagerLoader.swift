import Foundation

// MARK: - Tunnels Manager Loader

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
