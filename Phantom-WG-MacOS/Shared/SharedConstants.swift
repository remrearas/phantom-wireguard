import Foundation

enum SharedConstants {
    static let appGroupID = "group.com.remrearas.phantom-wg-macos"

    /// Location of the split-tunnelling configuration blob inside the
    /// shared App Group container. File-based storage (instead of
    /// UserDefaults) sidesteps the `cfprefsd` cross-process caching
    /// issue — both main app and extension read the same bytes off
    /// disk and atomic writes are cheap for our single-JSON payload.
    static var splitTunnelingConfigurationFileURL: URL? {
        guard let container = FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: appGroupID
        ) else {
            return nil
        }
        return container.appendingPathComponent("split-tunneling.json")
    }
}
