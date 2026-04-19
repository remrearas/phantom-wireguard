import Foundation
import NetworkExtension

// MARK: - Split Tunnel Provider Manager

/// Thin wrapper around `NETransparentProxyManager`. Handles the
/// "one transparent proxy per app" lifecycle: load the existing
/// configuration from system preferences, start/stop the proxy session
/// when the user flips the enable toggle, and remove the configuration
/// when the user uninstalls the extension.
///
/// Phase 1 uses this in skeleton mode — starting the session exercises
/// the full install → save → connect pipeline but the extension itself
/// declines every flow, so traffic routing is unaffected. Phase 2 plugs
/// the decision engine behind `handleNewFlow` and this manager becomes
/// the live orchestration point.
@Observable
@MainActor
class SplitTunnelProviderManager {

    enum SessionStatus: Equatable {
        case disconnected
        case connecting
        case connected
        case disconnecting
        case invalid
    }

    var sessionStatus: SessionStatus = .disconnected
    var lastError: String?

    @ObservationIgnored private var manager: NETransparentProxyManager?
    @ObservationIgnored private var statusObserver: NSObjectProtocol?

    private static let providerBundleID = "com.remrearas.Phantom-WG-MacOS.PhantomSplitTunnel"
    private static let localizedDescription = "Phantom-WG Split-Tunnel"

    // MARK: - Load

    /// Discover or create the preference entry. Called after the system
    /// extension reports `.activated`; before that `saveToPreferences`
    /// would fail because the OS has no registered provider.
    func load() async {
        do {
            let managers = try await NETransparentProxyManager.loadAllFromPreferences()
            manager = managers.first ?? NETransparentProxyManager()
            attachStatusObserver()
            refreshSessionStatus()
        } catch {
            NSLog("[SplitMgr] load failed: \(error)")
            lastError = error.localizedDescription
        }
    }

    // MARK: - Enable / Disable

    func enable() async throws {
        guard let manager else {
            throw ManagerError.notLoaded
        }

        let proto = NETunnelProviderProtocol()
        proto.providerBundleIdentifier = Self.providerBundleID
        proto.serverAddress = "127.0.0.1"
        manager.protocolConfiguration = proto
        manager.localizedDescription = Self.localizedDescription
        manager.isEnabled = true

        try await manager.saveToPreferences()
        try await manager.loadFromPreferences()
        try manager.connection.startVPNTunnel()
    }

    func disable() async throws {
        guard let manager else { return }
        manager.connection.stopVPNTunnel()
        manager.isEnabled = false
        try? await manager.saveToPreferences()
    }

    // MARK: - Uninstall

    /// Removes the preference entry entirely. Paired with
    /// `SplitTunnelExtensionState.deactivate()` in the uninstall flow.
    func removeConfiguration() async throws {
        guard let manager else { return }
        try await manager.removeFromPreferences()
        self.manager = nil
        sessionStatus = .disconnected
    }

    // MARK: - Observation

    private func attachStatusObserver() {
        if let existing = statusObserver {
            NotificationCenter.default.removeObserver(existing)
            statusObserver = nil
        }
        guard let manager else { return }

        statusObserver = NotificationCenter.default.addObserver(
            forName: .NEVPNStatusDidChange,
            object: manager.connection,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in
                self?.refreshSessionStatus()
            }
        }
    }

    private func refreshSessionStatus() {
        guard let manager else {
            sessionStatus = .disconnected
            return
        }
        switch manager.connection.status {
        case .connected:     sessionStatus = .connected
        case .connecting, .reasserting: sessionStatus = .connecting
        case .disconnecting: sessionStatus = .disconnecting
        case .disconnected:  sessionStatus = .disconnected
        case .invalid:       sessionStatus = .invalid
        @unknown default:    sessionStatus = .invalid
        }
    }

    deinit {
        if let observer = statusObserver {
            NotificationCenter.default.removeObserver(observer)
        }
    }

    // MARK: - Errors

    enum ManagerError: LocalizedError {
        case notLoaded

        var errorDescription: String? {
            switch self {
            case .notLoaded:
                return "Split-tunnel provider manager not loaded."
            }
        }
    }
}
