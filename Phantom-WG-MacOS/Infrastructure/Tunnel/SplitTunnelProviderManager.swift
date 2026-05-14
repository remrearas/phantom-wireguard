import Foundation
import NetworkExtension

/// Wraps `NETransparentProxyManager`. Owns the preference entry
/// lifecycle and surfaces three opcode RPCs to the running session
/// (config reload, log fetch, log clear).
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

    @ObservationIgnored private var manager: NETransparentProxyManager?
    @ObservationIgnored private var statusObserver: NSObjectProtocol?

    private static let providerBundleID = "com.remrearas.Phantom-WG-MacOS.PhantomSplitTunnel"
    private static let localizedDescription = "Phantom-WG Split-Tunnel"

    // MARK: - Load

    /// Discovers or creates the preference entry. Must be called
    /// after the system extension reports `.activated`.
    func load() async {
        do {
            let managers = try await NETransparentProxyManager.loadAllFromPreferences()
            manager = managers.first ?? NETransparentProxyManager()
            attachStatusObserver()
            refreshSessionStatus()
        } catch {
            // load is non-fatal — the gate retries via reload.
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

    // MARK: - Provider Messaging

    /// Opcode `0x00` — live reload. Payload = opcode byte + JSON
    /// configuration. No-op when the session isn't connected.
    func reloadExtensionConfig(with configuration: SplitTunnelingConfiguration) async {
        guard let configData = try? JSONEncoder().encode(configuration) else { return }
        var message = Data([0x00])
        message.append(configData)
        _ = await sendOpcode(message)
    }

    /// Opcode `0x02` — flush the extension's log ring buffer.
    func clearLogs() async {
        _ = await sendOpcode(Data([0x02]))
    }

    /// Opcode `0x01` — newline-joined log snapshot, or `nil` if the
    /// session isn't up.
    func fetchLogs() async -> String? {
        guard let data = await sendOpcode(Data([0x01])) else { return nil }
        return String(data: data, encoding: .utf8)
    }

    /// Send an opcode (and inline payload) to the running extension.
    /// Returns the reply bytes, or `nil` if the session isn't
    /// connected or the call throws.
    private func sendOpcode(_ message: Data) async -> Data? {
        guard let manager,
              let session = manager.connection as? NETunnelProviderSession,
              session.status == .connected else {
            return nil
        }
        return await withCheckedContinuation { (continuation: CheckedContinuation<Data?, Never>) in
            do {
                try session.sendProviderMessage(message) { reply in
                    continuation.resume(returning: reply)
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
