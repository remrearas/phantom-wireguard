import SwiftUI

/// Footer actions — copy-to-clipboard and delete. The copy button owns
/// its own "Copied!" feedback timer locally; delete is routed back to
/// the parent's confirmation dialog via a binding so the destructive
/// action lives at the view root.
struct ActionsSection: View {
    var tunnel: TunnelContainer
    let copyAction: () -> Void
    @Binding var showingDeleteConfirmation: Bool
    @State private var copiedItem: String?
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        Section {
            copyButton(loc.t("detail_copy_conf"), icon: "doc.text", id: "conf") { copyAction() }
                .listRowSeparator(.hidden)
                .accessibilityIdentifier(AXID.TunnelDetail.Actions.copyButton)

            Button(role: .destructive) {
                showingDeleteConfirmation = true
            } label: {
                Label(loc.t("detail_delete_tunnel"), systemImage: "trash")
            }
            .disabled(tunnel.status != .inactive)
            .listRowSeparator(.hidden)
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
