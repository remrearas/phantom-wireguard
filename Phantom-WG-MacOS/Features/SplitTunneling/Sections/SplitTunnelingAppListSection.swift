import SwiftUI

/// Scrollable list of picked applications plus the "Add Application…"
/// entry point. Empty state is surfaced as a single caption row rather
/// than a full-size view to keep the sheet's vertical rhythm stable.
struct SplitTunnelingAppListSection: View {
    let apps: [AppEntry]
    let isDisabled: Bool
    let onAddApp: () -> Void
    let onRemoveApp: (String) -> Void
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        Section {
            if apps.isEmpty {
                Text(loc.t("split_tunneling_empty_state"))
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 4)
                    .accessibilityIdentifier(AXID.SplitTunneling.emptyState)
            } else {
                ForEach(apps) { entry in
                    AppEntryRow(entry: entry, onRemove: { onRemoveApp(entry.bundleIdentifier) })
                }
            }

            Button(action: onAddApp) {
                Label(loc.t("split_tunneling_add_app"), systemImage: "plus")
            }
            .accessibilityIdentifier(AXID.SplitTunneling.addAppButton)
        } header: {
            Label(loc.t("split_tunneling_exclude_applications"), systemImage: "app.badge.checkmark")
                .padding(.leading, 4)
        } footer: {
            Text(loc.t("split_tunneling_exclude_applications_footer"))
                .padding(.leading, 4)
        }
        .disabled(isDisabled)
        .opacity(isDisabled ? 0.5 : 1.0)
    }
}
