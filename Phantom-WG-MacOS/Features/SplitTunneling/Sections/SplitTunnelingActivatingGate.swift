import SwiftUI

/// Transient gate shown while the activation request is in flight,
/// before macOS either finishes (`.activated`) or asks for approval
/// (`.needsApproval`). Plain spinner + label — mirrors the main app's
/// `ActivatingView` for the tunnel extension.
struct SplitTunnelingActivatingGate: View {
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        VStack(spacing: 16) {
            ProgressView()
                .controlSize(.large)

            Text(loc.t("split_tunneling_installing"))
                .font(.callout)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
