import SwiftUI

/// Single-tap TR↔EN language toggle. Shows the flag of the *other*
/// language so the label reads as the action the user is about to
/// take. The switch itself is a one-shot write to
/// `LocalizationManager.current`, which propagates through the
/// environment and re-renders all views that call `loc.t(_:)`.
struct LanguageToggleButton: View {
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        Button {
            loc.current = loc.current == .tr ? .en : .tr
        } label: {
            Text(loc.current == .tr
                 ? LocalizationManager.Language.en.flag
                 : LocalizationManager.Language.tr.flag)
                .font(.title2)
        }
        .accessibilityIdentifier(AXID.TunnelList.languageToggle)
    }
}
