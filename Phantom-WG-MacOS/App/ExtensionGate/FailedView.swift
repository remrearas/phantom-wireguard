import SwiftUI

/// Terminal failure screen — surfaces whatever localized message the
/// system extension activation produced and offers a retry button
/// that re-submits the activation request.
struct FailedView: View {
    let message: String
    let onRetry: () -> Void
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 48))
                .foregroundStyle(.red)

            Text(loc.t("sysext_failed_title"))
                .font(.headline)

            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
                .accessibilityIdentifier(AXID.ExtensionGate.failedMessage)

            Button(loc.t("sysext_retry")) {
                onRetry()
            }
            .buttonStyle(.borderedProminent)
            .accessibilityIdentifier(AXID.ExtensionGate.failedRetry)
        }
    }
}
