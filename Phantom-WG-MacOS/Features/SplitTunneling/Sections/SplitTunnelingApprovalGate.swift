import SwiftUI

/// Blocks the form while macOS waits for the user to approve the
/// system extension in System Settings. The approval polling inside
/// `SplitTunnelExtensionState` automatically flips the state back to
/// `.activated` once the user grants permission, so this gate tends to
/// resolve on its own without the "Check Again" button being needed.
struct SplitTunnelingApprovalGate: View {
    let onOpenSettings: () -> Void
    let onCheckAgain: () -> Void
    @Environment(LocalizationManager.self) private var loc

    private var approvalMessage: String {
        if #available(macOS 15.0, *) {
            return loc.t("split_tunneling_approval_message_sequoia")
        } else {
            return loc.t("split_tunneling_approval_message_sonoma")
        }
    }

    var body: some View {
        VStack(spacing: 20) {
            Spacer()

            Image(systemName: "lock.shield")
                .resizable()
                .scaledToFit()
                .frame(width: 64, height: 64)
                .foregroundStyle(.orange)

            Text(loc.t("split_tunneling_approval_title"))
                .font(.title2.weight(.semibold))

            Text(.init(approvalMessage))
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 40)
                .fixedSize(horizontal: false, vertical: true)

            HStack(spacing: 12) {
                Button(loc.t("sysext_open_settings"), action: onOpenSettings)
                    .buttonStyle(.borderedProminent)
                    .accessibilityIdentifier(AXID.SplitTunneling.openSettings)

                Button(loc.t("sysext_check_again"), action: onCheckAgain)
                    .accessibilityIdentifier(AXID.SplitTunneling.checkAgain)
            }
            .controlSize(.large)

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
