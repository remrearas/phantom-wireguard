import Foundation
import AppKit
import Observation

/// Single source of truth for the app-wide split tunneling configuration
/// in the **main app process**.
///
/// Persists the config as a JSON blob on disk inside the shared App
/// Group container. File-based storage instead of UserDefaults because
/// `cfprefsd` caches per-process and detaches when the extension
/// (sandboxed) can't talk to the daemon — we saw "reload: 0 app(s)"
/// even after the main app wrote new entries.
///
/// The App Group path lives in `SharedConstants` and is technically
/// visible to both processes, but only the main app reads or writes
/// this file. The extension receives the configuration through
/// `providerConfiguration["split_config"]` at `startProxy` and via
/// opcode `0x00` live-reload messages afterwards — not via this file.
@Observable
@MainActor
final class SplitTunnelingStore {

    // MARK: - State

    private(set) var configuration: SplitTunnelingConfiguration

    /// Wired at app startup. Every configuration mutation asks the
    /// provider manager to fire a live reload on the extension if the
    /// session is currently up; a no-op otherwise. Weak to avoid the
    /// manager → store cycle since the manager doesn't need the store.
    @ObservationIgnored weak var providerManager: SplitTunnelProviderManager?

    // MARK: - Init

    /// Production: no argument — persists to the App Group container
    /// via `SharedConstants.splitTunnelingConfigurationFileURL`.
    ///
    /// Tests: pass an isolated `fileURL` so the persist/load cycle
    /// stays out of the user's real container. The resolver fallback
    /// remains `SharedConstants` so callers that don't care about
    /// injection get the production path without noise.
    init(fileURL: URL? = nil) {
        self.fileURLOverride = fileURL
        self.configuration = Self.loadFromDisk(fileURL: fileURL) ?? .default
    }

    @ObservationIgnored private let fileURLOverride: URL?

    private var effectiveFileURL: URL? {
        fileURLOverride ?? SharedConstants.splitTunnelingConfigurationFileURL
    }

    // MARK: - Mutation

    /// Flip the master gate. The app list is preserved so that
    /// re-enabling restores the user's last configuration exactly.
    func setEnabled(_ enabled: Bool) {
        configuration.isEnabled = enabled
        persist()
    }

    /// User picked a specific physical interface (or auto).
    func setInterfaceSelection(_ selection: InterfaceSelection) {
        configuration.interfaceSelection = selection
        persist()
        scheduleReload()
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
        scheduleReload()
        return true
    }

    func removeApp(bundleIdentifier: String) {
        configuration.apps.removeAll { $0.bundleIdentifier == bundleIdentifier }
        persist()
        scheduleReload()
    }

    /// Destructive: clears every field back to the first-run baseline.
    /// Called from the Reset action (confirmed via alert in the UI).
    func reset() {
        configuration = .default
        persist()
        scheduleReload()
    }

    // MARK: - Private

    /// Ask the extension to re-read the JSON blob. Safe to call when
    /// the session isn't up — the manager short-circuits and the
    /// extension picks up the fresh blob on its next `startProxy`.
    private func scheduleReload() {
        guard let providerManager else { return }
        let snapshot = configuration
        Task { await providerManager.reloadExtensionConfig(with: snapshot) }
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
        guard let url = effectiveFileURL else { return }
        do {
            let data = try JSONEncoder().encode(configuration)
            try FileManager.default.createDirectory(
                at: url.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            try data.write(to: url, options: .atomic)
        } catch {
            NSLog("[split-tunneling] persist failed: \(error)")
        }
    }

    private static func loadFromDisk(fileURL: URL?) -> SplitTunnelingConfiguration? {
        let url = fileURL ?? SharedConstants.splitTunnelingConfigurationFileURL
        guard let url, let data = try? Data(contentsOf: url) else {
            return nil
        }
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
