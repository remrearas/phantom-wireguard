import Foundation
import NetworkExtension

class TunnelContainer: ObservableObject, Identifiable {

    let tunnelProvider: TunnelProviding

    /// Stable identity captured at init. Using the persisted `TunnelConfig.id`
    /// keeps `ForEach` diffing correct across renames — unlike the display
    /// name, the UUID never changes once the tunnel is saved. A fresh UUID
    /// is used as fallback for transient states where no config is attached.
    let id: UUID

    @Published var name: String
    @Published var status: TunnelStatus
    @Published var lastActivationError: TunnelActivationError?

    var tunnelConfig: TunnelConfig? {
        tunnelProvider.tunnelConfig
    }

    // Activation tracking (used by TunnelsManager)
    var onDeactivated: ((TunnelContainer) -> Void)?
    var isAttemptingActivation = false
    var activationAttemptId: String?
    var activationTask: Task<Void, Never>?

    init(tunnel: TunnelProviding) {
        tunnelProvider = tunnel
        id = tunnel.tunnelConfig?.id ?? UUID()
        name = tunnel.localizedDescription ?? ""
        status = TunnelStatus(from: tunnel.connectionStatus)
    }

    func refreshStatus() {
        status = TunnelStatus(from: tunnelProvider.connectionStatus)
    }
}
