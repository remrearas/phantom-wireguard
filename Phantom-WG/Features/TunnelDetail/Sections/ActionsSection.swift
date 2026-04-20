import SwiftUI

/// Footer actions — copy config (.conf), copy logs, and destructive
/// delete. The copy buttons own their own "Copied!" feedback timer
/// locally; delete is routed back to the parent's confirmation dialog
/// via a binding so the destructive action lives at the view root.
/// Log clearing now lives in `LogView`'s toolbar, symmetrical with
/// the macOS counterpart and reachable from the same screen where
/// the entries are shown.
struct ActionsSection: View {
    var tunnel: TunnelContainer
    let copyConfAction: () -> Void
    let copyLogsAction: () -> Void
    @Binding var showingDeleteConfirmation: Bool
    @State private var copiedItem: String?
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        Section {
            copyButton(loc.t("detail_copy_conf"), icon: "doc.plaintext", id: "conf") { copyConfAction() }
                .accessibilityIdentifier(AXID.TunnelDetail.Actions.copyConf)
            copyButton(loc.t("detail_copy_logs"), icon: "text.quote", id: "logs") { copyLogsAction() }
                .accessibilityIdentifier(AXID.TunnelDetail.Actions.copyLogs)

            Button(role: .destructive) {
                showingDeleteConfirmation = true
            } label: {
                Label(loc.t("detail_delete_tunnel"), systemImage: "trash")
            }
            .disabled(tunnel.status != .inactive)
            .accessibilityIdentifier(AXID.TunnelDetail.Actions.deleteButton)
        } header: {
            Label(loc.t("detail_actions"), systemImage: "ellipsis.circle")
        }
    }

    private func copyButton(_ title: String, icon: String, id: String, action: @escaping () -> Void) -> some View {
        Button {
            action()
            copiedItem = id
            Task {
                try? await Task.sleep(for: .seconds(2))
                if copiedItem == id { copiedItem = nil }
            }
        } label: {
            Label(copiedItem == id ? loc.t("detail_copied") : title,
                  systemImage: copiedItem == id ? "checkmark.circle.fill" : icon)
            .foregroundStyle(copiedItem == id ? .green : .accentColor)
        }
    }
}
