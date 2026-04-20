import Foundation
import NetworkExtension

// MARK: - Split Tunnel Provider Manager

/// Thin wrapper around `NETransparentProxyManager`. Owns the
/// preference entry lifecycle: load, save-and-start when the user
/// flips the enable toggle, stop on disable, and clear the entry
/// entirely when the user uninstalls the extension.
///
/// Config is handed to the extension through the OS-managed
/// `providerConfiguration` dict at save time (initial boot path) and
/// through an inline `sendProviderMessage` payload afterwards (live
/// reload path). This avoids any cross-process file / UserDefaults
/// sync — both channels survive sandbox user-context mismatches that
/// App Group storage does not.
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
            lastError = error.localizedDescription
        }
    }

    // MARK: - Enable / Disable

    func enable(with configuration: SplitTunnelingConfiguration) async throws {
        guard let manager else {
            throw ManagerError.notLoaded
        }

        let proto = NETunnelProviderProtocol()
        proto.providerBundleIdentifier = Self.providerBundleID
        proto.serverAddress = "127.0.0.1"

        // Pack config bytes into providerConfiguration — this is the
        // OS-managed cross-process channel. Unlike App Group files,
        // `providerConfiguration` is visible to the extension regardless
        // of sandbox user context (root vs. user), which is how
        // PhantomTunnel reliably passes its tunnel config.
        if let data = try? JSONEncoder().encode(configuration) {
            proto.providerConfiguration = ["split_config": data]
        }

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

    // MARK: - Provider Messaging

    /// Opcode `0x00` — live config reload. The message payload is the
    /// opcode byte followed by the JSON-encoded configuration, so the
    /// extension applies the fresh bytes without touching any shared
    /// storage. No-op if the session isn't connected; the OS will
    /// re-read `providerConfiguration` on the next `startProxy`.
    func reloadExtensionConfig(with configuration: SplitTunnelingConfiguration) async {
        guard let manager,
              let session = manager.connection as? NETunnelProviderSession,
              session.status == .connected,
              let configData = try? JSONEncoder().encode(configuration) else {
            return
        }

        var message = Data([0x00])
        message.append(configData)

        _ = try? await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Data?, Error>) in
            do {
                try session.sendProviderMessage(message) { ackData in
                    continuation.resume(returning: ackData)
                }
            } catch {
                continuation.resume(throwing: error)
            }
        }
    }

    /// Opcode `0x02` — flush the extension's log ring buffer. No-op if
    /// the session isn't connected; the next `startProxy` starts with
    /// a fresh buffer regardless.
    func clearLogs() async {
        guard let manager,
              let session = manager.connection as? NETunnelProviderSession,
              session.status == .connected else {
            return
        }
        _ = try? await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Data?, Error>) in
            do {
                try session.sendProviderMessage(Data([0x02])) { ack in
                    continuation.resume(returning: ack)
                }
            } catch {
                continuation.resume(throwing: error)
            }
        }
    }

    /// Opcode `0x01` — log snapshot. Returns the newline-joined buffer
    /// shipped by the extension, or nil if the session isn't up.
    /// Used by the Logs view inside the Split-Tunneling sheet.
    func fetchLogs() async -> String? {
        guard let manager,
              let session = manager.connection as? NETunnelProviderSession,
              session.status == .connected else {
            return nil
        }
        return await withCheckedContinuation { (continuation: CheckedContinuation<String?, Never>) in
            do {
                try session.sendProviderMessage(Data([0x01])) { data in
                    guard let data else {
                        continuation.resume(returning: nil)
                        return
                    }
                    continuation.resume(returning: String(data: data, encoding: .utf8))
                }
            } catch {
                continuation.resume(returning: nil)
            }
        }
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
