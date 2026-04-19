import Foundation
import SystemExtensions

// MARK: - Split Tunnel Extension State

/// Activation lifecycle wrapper for the PhantomSplitTunnel system
/// extension. Structurally mirrors `SystemExtensionState` but is
/// scoped to the split-tunneling bundle so the two extensions can be
/// installed, approved and removed independently.
///
/// The main tunnel extension is a hard requirement for the app to be
/// functional at all; the split-tunnel extension is opt-in — the user
/// installs it from inside the Split-Tunneling sheet only when they
/// want the feature, and can remove it without touching the tunnel.
@Observable
@MainActor
class SplitTunnelExtensionState: NSObject, OSSystemExtensionRequestDelegate {

    enum Status: Equatable {
        case unknown
        case notInstalled
        case activating
        case needsApproval
        case activated
        case failed(String)
    }

    var status: Status = .unknown

    @ObservationIgnored private static let extensionBundleId = "com.remrearas.Phantom-WG-MacOS.PhantomSplitTunnel"
    @ObservationIgnored private var approvalPollTask: Task<Void, Never>?
    @ObservationIgnored private var deactivationContinuation: CheckedContinuation<Void, Error>?

    // MARK: - Activation

    func activate() {
        stopApprovalPolling()

        if status != .needsApproval {
            status = .activating
        }

        NSLog("[SplitExt] Activating: \(Self.extensionBundleId)")

        let request = OSSystemExtensionRequest.activationRequest(
            forExtensionWithIdentifier: Self.extensionBundleId,
            queue: .main
        )
        request.delegate = self
        OSSystemExtensionManager.shared.submitRequest(request)
    }

    // MARK: - Deactivation

    /// Submit a deactivation request and await completion. Unlike the
    /// main extension's uninstall, this is invoked from inside the
    /// Split-Tunneling sheet and leaves the tunnel extension intact.
    func deactivate() async throws {
        stopApprovalPolling()

        NSLog("[SplitExt] Deactivating: \(Self.extensionBundleId)")

        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            self.deactivationContinuation = continuation

            let request = OSSystemExtensionRequest.deactivationRequest(
                forExtensionWithIdentifier: Self.extensionBundleId,
                queue: .main
            )
            request.delegate = self
            OSSystemExtensionManager.shared.submitRequest(request)
        }
    }

    private func resumeDeactivation(with result: Result<Void, Error>) {
        guard let continuation = deactivationContinuation else { return }
        deactivationContinuation = nil
        continuation.resume(with: result)
    }

    // MARK: - Approval Polling

    private func startApprovalPolling() {
        stopApprovalPolling()
        approvalPollTask = Task { [weak self] in
            while !Task.isCancelled {
                do {
                    try await Task.sleep(for: .seconds(3))
                } catch { return }
                guard let self, self.status == .needsApproval else { return }
                NSLog("[SplitExt] Polling: re-submitting activation request")
                self.activate()
            }
        }
    }

    private func stopApprovalPolling() {
        approvalPollTask?.cancel()
        approvalPollTask = nil
    }

    // MARK: - OSSystemExtensionRequestDelegate

    nonisolated func request(
        _ request: OSSystemExtensionRequest,
        actionForReplacingExtension existing: OSSystemExtensionProperties,
        withExtension ext: OSSystemExtensionProperties
    ) -> OSSystemExtensionRequest.ReplacementAction {
        NSLog("[SplitExt] Replacing existing extension (v\(existing.bundleShortVersion) → v\(ext.bundleShortVersion))")
        return .replace
    }

    nonisolated func requestNeedsUserApproval(_ request: OSSystemExtensionRequest) {
        NSLog("[SplitExt] Needs user approval")
        Task { @MainActor in
            status = .needsApproval
            startApprovalPolling()
        }
    }

    nonisolated func request(
        _ request: OSSystemExtensionRequest,
        didFinishWithResult result: OSSystemExtensionRequest.Result
    ) {
        NSLog("[SplitExt] Finished with result: \(result.rawValue)")
        Task { @MainActor in
            stopApprovalPolling()

            if deactivationContinuation != nil {
                NSLog("[SplitExt] Deactivation completed")
                status = .notInstalled
                resumeDeactivation(with: .success(()))
                return
            }

            switch result {
            case .completed:
                status = .activated
            case .willCompleteAfterReboot:
                NSLog("[SplitExt] Will complete after reboot")
                status = .needsApproval
            @unknown default:
                status = .activated
            }
        }
    }

    nonisolated func request(
        _ request: OSSystemExtensionRequest,
        didFailWithError error: Error
    ) {
        let nsError = error as NSError
        let code = nsError.code
        let domain = nsError.domain
        NSLog("[SplitExt] Failed: domain=\(domain) code=\(code) — \(error.localizedDescription)")

        Task { @MainActor in
            stopApprovalPolling()

            if deactivationContinuation != nil {
                resumeDeactivation(with: .failure(error))
                return
            }

            guard domain == OSSystemExtensionErrorDomain else {
                status = .failed(error.localizedDescription)
                return
            }

            handleActivationFailure(code: code, error: error)
        }
    }

    // MARK: - Failure Mapping

    private func handleActivationFailure(code: Int, error: Error) {
        let loc = LocalizationManager.shared

        switch OSSystemExtensionError.Code(rawValue: code) {
        case .requestCanceled, .requestSuperseded:
            NSLog("[SplitExt] Request canceled/superseded, ignoring")
        case .authorizationRequired:
            status = .needsApproval
            startApprovalPolling()
        case .unsupportedParentBundleLocation:
            status = .failed(loc.t("sysext_err_unsupported_location"))
        case .extensionNotFound:
            status = .notInstalled
        case .codeSignatureInvalid:
            status = .failed(loc.t("sysext_err_code_signature"))
        case .validationFailed:
            status = .failed(loc.t("sysext_err_validation"))
        case .forbiddenBySystemPolicy:
            status = .failed(loc.t("sysext_err_system_policy"))
        case .missingEntitlement:
            status = .failed(loc.t("sysext_err_entitlement"))
        default:
            status = .failed(loc.t("sysext_err_unknown", code, error.localizedDescription))
        }
    }
}
