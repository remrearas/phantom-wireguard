import SwiftUI

/// Shown while the OS is loading / installing the system extension on
/// first launch. Pure presentation — activation is driven from the
/// root view's `onAppear`.
struct ActivatingView: View {
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        VStack(spacing: 20) {
            Image("PhantomLogo")
                .resizable()
                .scaledToFit()
                .frame(width: 120, height: 120)
            ProgressView(loc.t("sysext_activating"))
                .tint(.secondary)
        }
    }
}
