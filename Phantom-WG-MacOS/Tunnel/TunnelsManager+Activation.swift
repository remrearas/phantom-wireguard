import Foundation
import NetworkExtension

// MARK: - Activation & Deactivation

extension TunnelsManager {

    func startActivation(of tunnel: TunnelContainer) {
        guard tunnel.status == .inactive else { return }

        if let activeTunnel = tunnels.first(where: { $0.status != .inactive && $0.status != .waiting }) {
            if let previousWaiting = waitingTunnel, previousWaiting.id != tunnel.id {
                previousWaiting.status = .inactive
            }
            tunnel.status = .waiting
            waitingTunnel = tunnel
            startDeactivation(of: activeTunnel)
            return
        }

        startActivation(of: tunnel, at: 0)
    }

    func startDeactivation(of tunnel: TunnelContainer) {
        guard tunnel.status != .inactive && tunnel.status != .deactivating else { return }
        performDeactivation(of: tunnel)
    }

    // MARK: - Private

    func startActivation(of tunnel: TunnelContainer, at retryIndex: Int) {
        guard retryIndex < maxRetries else {
            tunnel.isAttemptingActivation = false
            tunnel.activationTask?.cancel()
            tunnel.activationTask = nil
            tunnel.status = .inactive
            tunnel.lastActivationError = .retryLimitReached(
                lastSystemError: NSError(domain: NEVPNErrorDomain, code: 1))
            return
        }

        if retryIndex == 0 {
            tunnel.status = .activating
            tunnel.lastActivationError = nil
        }

        tunnel.isAttemptingActivation = true
        let attemptId = UUID().uuidString
        tunnel.activationAttemptId = attemptId

        tunnel.tunnelProvider.isEnabled = true
        Task {
            do {
                try await tunnel.tunnelProvider.savePreferences()
                guard tunnel.activationAttemptId == attemptId else { return }
                await self.doStartVPNTunnel(tunnel: tunnel, attemptId: attemptId, retryIndex: retryIndex)
            } catch {
                tunnel.isAttemptingActivation = false
                tunnel.status = .inactive
                tunnel.lastActivationError = .savingFailed(systemError: error)
            }
        }
    }

    func doStartVPNTunnel(tunnel: TunnelContainer, attemptId: String, retryIndex: Int) async {
        do {
            try await tunnel.tunnelProvider.loadPreferences()
        } catch {
            tunnel.isAttemptingActivation = false
            tunnel.status = .inactive
            tunnel.lastActivationError = .loadingFailed(systemError: error)
            return
        }

        guard tunnel.activationAttemptId == attemptId else { return }

        do {
            try tunnel.tunnelProvider.startTunnel()
        } catch {
            tunnel.isAttemptingActivation = false
            tunnel.status = .inactive
            tunnel.lastActivationError = .startingFailed(systemError: error)
            return
        }

        // Retry task — if still activating after interval, retry
        tunnel.activationTask?.cancel()
        let tunnelId = tunnel.id
        tunnel.activationTask = Task { [weak self] in
            do {
                try await Task.sleep(for: .seconds(self?.retryInterval ?? 5.0))
            } catch {
                return
            }
            guard let self,
                  let tunnel = self.tunnels.first(where: { $0.id == tunnelId }),
                  tunnel.activationAttemptId == attemptId else { return }
            if tunnel.status == .activating || tunnel.status == .reasserting {
                self.startActivation(of: tunnel, at: retryIndex + 1)
            }
        }
    }

    func performDeactivation(of tunnel: TunnelContainer) {
        tunnel.status = .deactivating
        tunnel.tunnelProvider.stopTunnel()
    }

    func activateWaitingTunnelIfNeeded() {
        guard let waitingTunnel else { return }
        self.waitingTunnel = nil
        guard waitingTunnel.status == .waiting else { return }
        startActivation(of: waitingTunnel, at: 0)
    }
}
