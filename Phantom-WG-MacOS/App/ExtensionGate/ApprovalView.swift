import SwiftUI
import AppKit

/// Prompts the user to allow the network extension in System Settings.
/// Opens the correct pane for Sonoma vs Sequoia+ and offers a "Check
/// Again" action that re-submits the activation request — used when
/// the OS lingers on `.needsApproval` despite the user having granted
/// permission.
struct ApprovalView: View {
    let onOpenSettings: () -> Void
    let onCheckAgain: () -> Void
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "shield.checkered")
                .font(.system(size: 48))
                .foregroundStyle(.orange)

            Text(loc.t("sysext_approval_title"))
                .font(.headline)

            Text(.init(approvalMessage))
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            Button(loc.t("sysext_open_settings")) {
                onOpenSettings()
            }
            .buttonStyle(.borderedProminent)
            .accessibilityIdentifier(AXID.ExtensionGate.approvalOpenSettings)

            Button(loc.t("sysext_check_again")) {
                onCheckAgain()
            }
            .buttonStyle(.bordered)
            .accessibilityIdentifier(AXID.ExtensionGate.approvalCheckAgain)
        }
    }

    private var approvalMessage: String {
        if #available(macOS 15.0, *) {
            return loc.t("sysext_approval_message_sequoia")
        } else {
            return loc.t("sysext_approval_message_sonoma")
        }
    }
}
