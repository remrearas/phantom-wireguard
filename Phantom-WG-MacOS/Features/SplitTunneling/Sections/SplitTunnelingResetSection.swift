import SwiftUI

/// Destructive reset action. Placed in its own section at the bottom
/// of the form to match the Delete-Tunnel affordance in TunnelDetail.
/// The confirmation alert is hosted by the parent view so the button
/// only needs to flip the binding.
struct SplitTunnelingResetSection: View {
    @Binding var showingResetConfirm: Bool
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        Section {
            Button(role: .destructive) {
                showingResetConfirm = true
            } label: {
                Label(loc.t("split_tunneling_reset"), systemImage: "arrow.counterclockwise")
                    .foregroundStyle(.red)
            }
            .accessibilityIdentifier(AXID.SplitTunneling.resetButton)
        }
    }
}
