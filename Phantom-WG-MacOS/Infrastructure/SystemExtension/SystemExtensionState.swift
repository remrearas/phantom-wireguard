import Foundation
import SystemExtensions

// MARK: - System Extension Activation State

@Observable
@MainActor
class SystemExtensionState: NSObject, OSSystemExtensionRequestDelegate {

    enum Status: Equatable {
        case unknown
        case activating
        case needsApproval
        case activated
        case deactivated
        case failed(String)
    }

    var status: Status = .unknown

    @ObservationIgnored private static let extensionBundleId = "com.remrearas.Phantom-WG-MacOS.PhantomTunnel"
    @ObservationIgnored private var approvalPollTask: Task<Void, Never>?
    @ObservationIgnored private var deactivationContinuation: CheckedContinuation<Void, Error>?

    func activate() {
        stopApprovalPolling()

        if status != .needsApproval {
            status = .activating
        }

        NSLog("[SysExt] Activating: \(Self.extensionBundleId)")

        let request = OSSystemExtensionRequest.activationRequest(
            forExtensionWithIdentifier: Self.extensionBundleId,
            queue: .main
        )
        request.delegate = self
        OSSystemExtensionManager.shared.submitRequest(request)
    }

    // MARK: - Deactivation

    /// Submit a deactivation request and wait for the result.
    /// Throws on failure; returns when the system confirms deactivation.
    /// The OS will prompt the user for password approval.
    func deactivate() async throws {
        stopApprovalPolling()

        NSLog("[SysExt] Deactivating: \(Self.extensionBundleId)")

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
                NSLog("[SysExt] Polling: re-submitting activation request")
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
        NSLog("[SysExt] Replacing existing extension (v\(existing.bundleShortVersion) → v\(ext.bundleShortVersion))")
        return .replace
    }

    nonisolated func requestNeedsUserApproval(_ request: OSSystemExtensionRequest) {
        NSLog("[SysExt] Needs user approval")
        Task { @MainActor in
            status = .needsApproval
            startApprovalPolling()
        }
    }

    nonisolated func request(
        _ request: OSSystemExtensionRequest,
        didFinishWithResult result: OSSystemExtensionRequest.Result
    ) {
        NSLog("[SysExt] Finished with result: \(result.rawValue)")
        Task { @MainActor in
            stopApprovalPolling()

            if deactivationContinuation != nil {
                NSLog("[SysExt] Deactivation completed")
                status = .deactivated
                resumeDeactivation(with: .success(()))
                return
            }

            switch result {
            case .completed:
                status = .activated
            case .willCompleteAfterReboot:
                NSLog("[SysExt] Will complete after reboot")
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
        NSLog("[SysExt] Failed: domain=\(domain) code=\(code) — \(error.localizedDescription)")

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

    /// Maps an `OSSystemExtensionError.Code` to a localized status update.
    /// Kept separate from the delegate method to keep cyclomatic complexity low.
    private func handleActivationFailure(code: Int, error: Error) {
        let loc = LocalizationManager.shared

        switch OSSystemExtensionError.Code(rawValue: code) {
        case .requestCanceled, .requestSuperseded:
            NSLog("[SysExt] Request canceled/superseded, ignoring")
        case .authorizationRequired:
            status = .needsApproval
            startApprovalPolling()
        case .unsupportedParentBundleLocation:
            status = .failed(loc.t("sysext_err_unsupported_location"))
        case .extensionNotFound:
            status = .failed(loc.t("sysext_err_not_found"))
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
