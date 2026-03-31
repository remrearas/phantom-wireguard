import Foundation
import SystemExtensions

// MARK: - System Extension Activation State

@MainActor
class SystemExtensionState: NSObject, ObservableObject, OSSystemExtensionRequestDelegate {

    enum Status: Equatable {
        case unknown
        case activating
        case needsApproval
        case activated
        case failed(String)
    }

    @Published var status: Status = .unknown

    private static let extensionBundleId = "com.remrearas.Phantom-WG-MacOS.PhantomTunnel"
    private var approvalPollTask: Task<Void, Never>?

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
            let loc = LocalizationManager.shared

            guard domain == OSSystemExtensionErrorDomain else {
                status = .failed(error.localizedDescription)
                return
            }

            switch OSSystemExtensionError.Code(rawValue: code) {
            case .requestCanceled, .requestSuperseded:
                NSLog("[SysExt] Request canceled/superseded, ignoring")
                return
            case .authorizationRequired:
                status = .needsApproval
                startApprovalPolling()
                return
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
}
