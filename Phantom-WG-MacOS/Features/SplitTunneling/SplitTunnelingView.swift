import SwiftUI

/// Sheet-hosted editor for the app-wide split tunneling configuration.
///
/// The sheet owns two lifecycles: the **PhantomSplitTunnel system
/// extension** (install → approve → activated → remove) and the
/// **feature state** (enabled/disabled + app list + reset). The full
/// form only appears once the extension is activated — earlier states
/// show install / approval / failure gates and hide the inner form
/// entirely so the user follows a linear path.
///
/// Every feature-level mutation is persisted eagerly to
/// `SplitTunnelingStore` (macOS System Settings pattern — no draft,
/// no explicit Save).
struct SplitTunnelingView: View {
    @Environment(SplitTunnelingStore.self) private var store
    @Environment(SplitTunnelExtensionState.self) private var extensionState
    @Environment(LocalizationManager.self) private var loc
    @Environment(\.dismiss) private var dismiss

    @State private var validationError: AppBundleValidator.ValidationError?
    @State private var duplicateError = false
    @State private var showingValidationError = false
    @State private var showingResetConfirm = false
    @State private var showingRemoveExtensionConfirm = false
    @State private var removingExtension = false
    @State private var showingRemoveError = false
    @State private var removeErrorMessage: String?

    var body: some View {
        content
            .frame(minWidth: 520, minHeight: 600)
            .navigationTitle(loc.t("split_tunneling_title"))
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button(loc.t("split_tunneling_close")) { dismiss() }
                        .accessibilityIdentifier(AXID.SplitTunneling.closeButton)
                }
            }
            .accessibilityIdentifier(AXID.SplitTunneling.sheet)
            .onAppear(perform: onSheetAppear)
            .disabled(removingExtension)
            .modifier(ValidationAlert(
                showingValidationError: $showingValidationError,
                messageProvider: { validationErrorMessage }
            ))
            .modifier(ResetAlert(
                showingResetConfirm: $showingResetConfirm,
                onReset: { store.reset() }
            ))
            .modifier(RemoveExtensionAlert(
                showingRemoveConfirm: $showingRemoveExtensionConfirm,
                showingRemoveError: $showingRemoveError,
                errorMessage: $removeErrorMessage,
                onConfirm: runRemoveExtension
            ))
    }

    // MARK: - State Machine

    @ViewBuilder
    private var content: some View {
        switch extensionState.status {
        case .unknown, .activating:
            SplitTunnelingActivatingGate()

        case .notInstalled:
            SplitTunnelingInstallGate(onInstall: extensionState.activate)

        case .needsApproval:
            SplitTunnelingApprovalGate(
                onOpenSettings: openSystemSettings,
                onCheckAgain: extensionState.activate
            )

        case .failed(let message):
            SplitTunnelingFailedGate(
                message: message,
                onRetry: extensionState.activate
            )

        case .activated:
            activatedContent
        }
    }

    private var activatedContent: some View {
        Form {
            SplitTunnelingEnableSection(
                isEnabled: Binding(
                    get: { store.configuration.isEnabled },
                    set: { store.setEnabled($0) }
                )
            )

            SplitTunnelingAppListSection(
                apps: store.configuration.apps,
                isDisabled: !store.configuration.isEnabled,
                onAddApp: handleAddApp,
                onRemoveApp: { store.removeApp(bundleIdentifier: $0) }
            )

            SplitTunnelingResetSection(
                showingResetConfirm: $showingResetConfirm
            )

            SplitTunnelingRemoveExtensionSection(
                showingRemoveConfirm: $showingRemoveExtensionConfirm,
                isRemoving: removingExtension
            )
        }
        .formStyle(.grouped)
    }

    // MARK: - Lifecycle

    /// Kick off an activation check only on the very first time the
    /// sheet appears (state still `.unknown`). After the user explicitly
    /// removes the extension (status `.notInstalled`) they must click
    /// Install to trigger a new request — otherwise re-opening the
    /// sheet would silently reinstall something they just uninstalled.
    private func onSheetAppear() {
        store.reconcile()
        if extensionState.status == .unknown {
            extensionState.activate()
        }
    }

    private func openSystemSettings() {
        if #available(macOS 15.0, *) {
            NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.LoginItems-Settings.extension")!)
        } else {
            NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles")!)
        }
    }

    // MARK: - Add App Flow

    private func handleAddApp() {
        let panel = NSOpenPanel()
        panel.title = loc.t("split_tunneling_picker_prompt")
        panel.prompt = loc.t("split_tunneling_add_app")
        panel.allowedContentTypes = [.application]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        panel.directoryURL = URL(fileURLWithPath: "/Applications")

        guard panel.runModal() == .OK, let url = panel.url else { return }

        switch AppBundleValidator.validate(url: url) {
        case .success(let entry):
            let added = store.addApp(entry)
            if !added {
                duplicateError = true
                validationError = nil
                showingValidationError = true
            }
        case .failure(let error):
            validationError = error
            duplicateError = false
            showingValidationError = true
        }
    }

    private var validationErrorMessage: String {
        if duplicateError {
            return loc.t("split_tunneling_err_duplicate")
        }
        guard let error = validationError else { return "" }
        switch error {
        case .notABundle:         return loc.t("split_tunneling_err_not_a_bundle")
        case .noBundleIdentifier: return loc.t("split_tunneling_err_no_bundle_id")
        case .notSigned:          return loc.t("split_tunneling_err_not_signed")
        case .noTeamIdentifier:   return loc.t("split_tunneling_err_no_team_id")
        }
    }

    // MARK: - Remove Extension Flow

    private func runRemoveExtension() {
        removingExtension = true
        Task {
            do {
                try await extensionState.deactivate()
            } catch {
                removeErrorMessage = error.localizedDescription
                showingRemoveError = true
            }
            removingExtension = false
        }
    }
}

// MARK: - Alert Modifiers

private struct ValidationAlert: ViewModifier {
    @Binding var showingValidationError: Bool
    let messageProvider: () -> String
    @Environment(LocalizationManager.self) private var loc

    func body(content: Content) -> some View {
        content.alert(loc.t("error"), isPresented: $showingValidationError) {
            Button(loc.t("ok")) {}
                .accessibilityIdentifier(AXID.SplitTunneling.errorAlertOK)
        } message: {
            Text(messageProvider())
        }
    }
}

private struct ResetAlert: ViewModifier {
    @Binding var showingResetConfirm: Bool
    let onReset: () -> Void
    @Environment(LocalizationManager.self) private var loc

    func body(content: Content) -> some View {
        content.alert(loc.t("split_tunneling_reset_confirm_title"),
                      isPresented: $showingResetConfirm) {
            Button(loc.t("cancel"), role: .cancel) {}
                .accessibilityIdentifier(AXID.SplitTunneling.resetCancel)
            Button(loc.t("split_tunneling_reset"), role: .destructive, action: onReset)
                .accessibilityIdentifier(AXID.SplitTunneling.resetConfirm)
        } message: {
            Text(loc.t("split_tunneling_reset_confirm_message"))
        }
    }
}

private struct RemoveExtensionAlert: ViewModifier {
    @Binding var showingRemoveConfirm: Bool
    @Binding var showingRemoveError: Bool
    @Binding var errorMessage: String?
    let onConfirm: () -> Void
    @Environment(LocalizationManager.self) private var loc

    func body(content: Content) -> some View {
        content
            .alert(loc.t("split_tunneling_remove_confirm_title"),
                   isPresented: $showingRemoveConfirm) {
                Button(loc.t("cancel"), role: .cancel) {}
                    .accessibilityIdentifier(AXID.SplitTunneling.removeCancel)
                Button(loc.t("split_tunneling_remove_extension"),
                       role: .destructive, action: onConfirm)
                    .accessibilityIdentifier(AXID.SplitTunneling.removeConfirm)
            } message: {
                Text(loc.t("split_tunneling_remove_confirm_message"))
            }
            .alert(loc.t("error"), isPresented: $showingRemoveError) {
                Button(loc.t("ok")) {}
            } message: {
                Text(errorMessage ?? "")
            }
    }
}
