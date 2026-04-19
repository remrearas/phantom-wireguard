import SwiftUI

/// Destructive section for removing the PhantomSplitTunnel system
/// extension. Unlike the gear-menu "Uninstall" which deactivates both
/// system extensions, this button only targets the split-tunneling
/// extension — the main tunnel and active tunnels are unaffected.
struct SplitTunnelingRemoveExtensionSection: View {
    @Binding var showingRemoveConfirm: Bool
    let isRemoving: Bool
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        Section {
            Button(role: .destructive) {
                showingRemoveConfirm = true
            } label: {
                Label(loc.t("split_tunneling_remove_extension"), systemImage: "trash")
                    .foregroundStyle(.red)
            }
            .disabled(isRemoving)
            .accessibilityIdentifier(AXID.SplitTunneling.removeExtension)
        }
    }
}
