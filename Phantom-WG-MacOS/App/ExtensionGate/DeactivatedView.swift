import SwiftUI
import AppKit

/// Shown after a successful uninstall. Guides the user to complete
/// removal by dragging the app to the Trash or offers to reinstall
/// the system extension to continue using the app.
struct DeactivatedView: View {
    let onReinstall: () -> Void
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "checkmark.shield.fill")
                .font(.system(size: 48))
                .foregroundStyle(.green)

            Text(loc.t("sysext_deactivated_title"))
                .font(.headline)

            Text(loc.t("sysext_deactivated_message"))
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            Button(loc.t("sysext_deactivated_reinstall")) {
                onReinstall()
            }
            .buttonStyle(.borderedProminent)
            .accessibilityIdentifier(AXID.ExtensionGate.deactivatedReinstall)

            Button(loc.t("sysext_deactivated_quit")) {
                NSApp.terminate(nil)
            }
            .buttonStyle(.bordered)
            .accessibilityIdentifier(AXID.ExtensionGate.deactivatedQuit)
        }
    }
}
