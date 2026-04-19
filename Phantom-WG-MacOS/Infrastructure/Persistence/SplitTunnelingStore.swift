import Foundation
import AppKit
import Observation

/// Single source of truth for the app-wide split tunneling configuration.
///
/// Persists the config as a JSON blob in the shared App Group
/// `UserDefaults` under a single key, so the system extension can read
/// the exact same object without any bespoke IPC. The main app owns
/// writes and periodic reconcile; the extension will only read.
///
/// Reconcile drops entries whose bundle identifier no longer resolves
/// on the system (user uninstalled the app). This keeps the state safe
/// for the tunnel layer — activation never trips over stale data.
@Observable
final class SplitTunnelingStore {

    // MARK: - Keys

    private static let defaultsKey = "split-tunneling.configuration"

    // MARK: - State

    private(set) var configuration: SplitTunnelingConfiguration

    @ObservationIgnored private let defaults: UserDefaults

    // MARK: - Init

    init(defaults: UserDefaults? = UserDefaults(suiteName: SharedConstants.appGroupID)) {
        self.defaults = defaults ?? .standard
        self.configuration = Self.load(from: self.defaults) ?? .default
    }

    // MARK: - Mutation

    /// Flip the master gate. The app list is preserved so that
    /// re-enabling restores the user's last configuration exactly.
    func setEnabled(_ enabled: Bool) {
        configuration.isEnabled = enabled
        persist()
    }

    /// Append a validated entry. Duplicates (by bundle identifier) are
    /// rejected at the validator layer; this method assumes the caller
    /// has already deduped and returns false if the dedup slipped through.
    @discardableResult
    func addApp(_ entry: AppEntry) -> Bool {
        guard !configuration.apps.contains(where: { $0.bundleIdentifier == entry.bundleIdentifier }) else {
            return false
        }
        configuration.apps.append(entry)
        persist()
        return true
    }

    func removeApp(bundleIdentifier: String) {
        configuration.apps.removeAll { $0.bundleIdentifier == bundleIdentifier }
        persist()
    }

    /// Destructive: clears every field back to the first-run baseline.
    /// Called from the Reset action (confirmed via alert in the UI).
    func reset() {
        configuration = .default
        persist()
    }

    // MARK: - Reconcile

    /// Drops entries whose bundle identifier no longer resolves via
    /// LaunchServices, and refreshes `lastKnownPath` + `displayName`
    /// for survivors (handles app reinstall paths).
    ///
    /// Runs on every tunnel activation and whenever the Split-Tunneling
    /// view is shown, so the tunnel layer never sees stale entries.
    func reconcile() {
        guard !configuration.apps.isEmpty else { return }

        var survivors: [AppEntry] = []
        for entry in configuration.apps {
            guard let url = NSWorkspace.shared.urlForApplication(
                withBundleIdentifier: entry.bundleIdentifier
            ) else {
                NSLog("[split-tunneling] reconcile: dropped '\(entry.bundleIdentifier)' (not installed)")
                continue
            }
            guard let bundle = Bundle(url: url),
                  bundle.bundleIdentifier == entry.bundleIdentifier else {
                NSLog("[split-tunneling] reconcile: dropped '\(entry.bundleIdentifier)' (path bundle ID mismatch)")
                continue
            }
            var updated = entry
            updated.lastKnownPath = url.path
            updated.displayName = Self.resolveDisplayName(bundle: bundle, url: url)
                ?? entry.displayName
            survivors.append(updated)
        }

        if survivors != configuration.apps {
            configuration.apps = survivors
            persist()
        }
    }

    // MARK: - Persistence

    private func persist() {
        do {
            let data = try JSONEncoder().encode(configuration)
            defaults.set(data, forKey: Self.defaultsKey)
        } catch {
            NSLog("[split-tunneling] persist failed: \(error)")
        }
    }

    private static func load(from defaults: UserDefaults) -> SplitTunnelingConfiguration? {
        guard let data = defaults.data(forKey: defaultsKey) else { return nil }
        return try? JSONDecoder().decode(SplitTunnelingConfiguration.self, from: data)
    }

    private static func resolveDisplayName(bundle: Bundle, url: URL) -> String? {
        if let name = bundle.infoDictionary?["CFBundleDisplayName"] as? String, !name.isEmpty {
            return name
        }
        if let name = bundle.infoDictionary?["CFBundleName"] as? String, !name.isEmpty {
            return name
        }
        return url.deletingPathExtension().lastPathComponent
    }
}
