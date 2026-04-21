import Foundation

enum SharedConstants {
    static let appGroupID = "group.com.remrearas.phantom-wg-macos"

    /// Location of the split-tunnelling configuration blob inside the
    /// shared App Group container. Used by the main app's
    /// `SplitTunnelingStore` for local persistence only — the
    /// extension never reads this file directly; it receives its
    /// config via `providerConfiguration["split_config"]` at
    /// `startProxy` and via opcode `0x00` live-reload afterwards.
    /// File-based storage (instead of UserDefaults) sidesteps the
    /// `cfprefsd` cross-process caching issue that would otherwise
    /// surface if the extension ever did need to read the blob in a
    /// different security context from the writer.
    static var splitTunnelingConfigurationFileURL: URL? {
        guard let container = FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: appGroupID
        ) else {
            return nil
        }
        return container.appendingPathComponent("split-tunneling.json")
    }
}
