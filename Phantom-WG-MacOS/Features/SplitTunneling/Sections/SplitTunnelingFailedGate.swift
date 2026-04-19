import SwiftUI

/// Terminal failure gate. Shown when `OSSystemExtensionRequest` returns
/// a non-recoverable error (missing entitlement, code signature
/// invalid, etc.). The Retry button simply re-submits the activation
/// request — useful for transient conditions; permanent failures need
/// the operator to fix signing / provisioning outside the app.
struct SplitTunnelingFailedGate: View {
    let message: String
    let onRetry: () -> Void
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        VStack(spacing: 20) {
            Spacer()

            Image(systemName: "exclamationmark.triangle.fill")
                .resizable()
                .scaledToFit()
                .frame(width: 64, height: 64)
                .foregroundStyle(.red)

            Text(loc.t("split_tunneling_failed_title"))
                .font(.title2.weight(.semibold))

            Text(message)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 40)
                .fixedSize(horizontal: false, vertical: true)

            Button(loc.t("split_tunneling_retry"), action: onRetry)
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .accessibilityIdentifier(AXID.SplitTunneling.retryButton)

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
