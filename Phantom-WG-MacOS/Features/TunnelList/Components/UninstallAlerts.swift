import SwiftUI

/// Pair of alerts attached to the tunnel list — one confirms the
/// destructive uninstall flow, the other surfaces any error raised
/// during its asynchronous steps. Bundled as a `ViewModifier` so the
/// list view body stays focused on layout.
struct UninstallAlerts: ViewModifier {
    @Binding var errorMessage: String?
    @Binding var showingError: Bool
    @Binding var showingUninstallConfirm: Bool
    let onConfirm: () -> Void
    @Environment(LocalizationManager.self) private var loc

    func body(content: Content) -> some View {
        content
            .alert(loc.t("error"), isPresented: $showingError) {
                Button(loc.t("ok")) {}
                    .accessibilityIdentifier(AXID.TunnelList.errorAlertOK)
            } message: {
                Text(errorMessage ?? "")
            }
            .alert(loc.t("uninstall_confirm_title"), isPresented: $showingUninstallConfirm) {
                Button(loc.t("cancel"), role: .cancel) {}
                    .accessibilityIdentifier(AXID.TunnelList.uninstallCancel)
                Button(loc.t("uninstall_confirm_action"), role: .destructive) {
                    onConfirm()
                }
                .accessibilityIdentifier(AXID.TunnelList.uninstallConfirm)
            } message: {
                Text(loc.t("uninstall_confirm_message"))
            }
    }
}
