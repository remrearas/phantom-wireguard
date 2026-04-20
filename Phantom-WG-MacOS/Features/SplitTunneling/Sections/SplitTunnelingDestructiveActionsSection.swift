import SwiftUI

/// Grouped destructive actions at the bottom of the sheet. Reset wipes
/// the user's feature configuration; Remove Extension tears down the
/// system extension itself. They share the same red treatment and sit
/// together so the operator doesn't reach across unrelated rows for a
/// destructive action.
///
/// Confirmation alerts are still hosted by `SplitTunnelingView` — this
/// section only surfaces the buttons and flips the matching binding.
struct SplitTunnelingDestructiveActionsSection: View {
    @Binding var showingResetConfirm: Bool
    @Binding var showingRemoveConfirm: Bool
    let isRemoving: Bool
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
