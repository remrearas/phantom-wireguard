import SwiftUI

/// First-run gate: no PhantomSplitTunnel system extension installed
/// yet. Surfaces a large icon + description + a single primary action
/// that fires `OSSystemExtensionRequest.activationRequest`. The user
/// then sees the approval gate once macOS asks for permission.
struct SplitTunnelingInstallGate: View {
    let onInstall: () -> Void
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        VStack(spacing: 20) {
            Spacer()

            Image(systemName: "arrow.triangle.branch")
                .resizable()
                .scaledToFit()
                .frame(width: 72, height: 72)
                .foregroundStyle(.secondary)

            Text(loc.t("split_tunneling_extension_title"))
                .font(.title2.weight(.semibold))

            Text(loc.t("split_tunneling_extension_description"))
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 40)
                .fixedSize(horizontal: false, vertical: true)

            Button(action: onInstall) {
                Label(loc.t("split_tunneling_install"), systemImage: "square.and.arrow.down")
                    .padding(.horizontal, 12)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .accessibilityIdentifier(AXID.SplitTunneling.installButton)

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
