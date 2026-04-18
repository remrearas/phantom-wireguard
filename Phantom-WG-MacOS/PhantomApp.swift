import SwiftUI

@main
struct PhantomApp: App {

    /// Skips system extension activation in the test environment.
    static var isRunningTests: Bool {
        ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] != nil
    }

    @StateObject private var extensionState = SystemExtensionState()
    @StateObject private var tunnelsManager = TunnelsManagerLoader()
    @StateObject private var loc = LocalizationManager.shared

    var body: some Scene {
        WindowGroup {
            Group {
                switch extensionState.status {
                case .unknown, .activating:
                    extensionActivatingView

                case .needsApproval:
                    extensionApprovalView

                case .activated:
                    tunnelContentView

                case .deactivated:
                    extensionDeactivatedView

                case .failed(let message):
                    extensionFailedView(message)
                }
            }
            .environmentObject(loc)
            .environmentObject(extensionState)
            .tint(Color.accentColor)
            .frame(width: 480, height: 720)
            .onAppear {
                guard !PhantomApp.isRunningTests else {
                    extensionState.status = .activated
                    return
                }
                extensionState.activate()
            }
        }
        .windowResizability(.contentSize)
    }

    private var approvalMessage: String {
        if #available(macOS 15.0, *) {
            return loc.t("sysext_approval_message_sequoia")
        } else {
            return loc.t("sysext_approval_message_sonoma")
        }
    }

    // MARK: - Extension States

    private var extensionActivatingView: some View {
        VStack(spacing: 20) {
            Image("PhantomLogo")
                .resizable()
                .scaledToFit()
                .frame(width: 120, height: 120)
            ProgressView(loc.t("sysext_activating"))
                .tint(.secondary)
        }
    }

    private var extensionApprovalView: some View {
        VStack(spacing: 20) {
            Image(systemName: "shield.checkered")
                .font(.system(size: 48))
                .foregroundStyle(.orange)

            Text(loc.t("sysext_approval_title"))
                .font(.headline)

            Text(.init(approvalMessage))
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            Button(loc.t("sysext_open_settings")) {
                if #available(macOS 15.0, *) {
                    // Sequoia+: Login Items & Extensions → Network Extensions
                    NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.LoginItems-Settings.extension")!)
                } else {
                    // Sonoma: Privacy & Security → Extensions
                    NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles")!)
                }
            }
            .buttonStyle(.borderedProminent)

            Button(loc.t("sysext_check_again")) {
                extensionState.activate()
            }
            .buttonStyle(.bordered)
        }
    }

    private var tunnelContentView: some View {
        Group {
            if let manager = tunnelsManager.manager {
                TunnelListView()
                    .environmentObject(manager)
            } else if let error = tunnelsManager.loadError {
                ContentUnavailableView(
                    loc.t("error"),
                    systemImage: "exclamationmark.triangle",
                    description: Text(error)
                )
            } else {
                VStack(spacing: 20) {
                    Image("PhantomLogo")
                        .resizable()
                        .scaledToFit()
                        .frame(width: 160, height: 160)
                    ProgressView(loc.t("app_loading"))
                        .tint(.secondary)
                }
                .task { await tunnelsManager.load() }
            }
        }
    }

    private var extensionDeactivatedView: some View {
        VStack(spacing: 20) {
            Image(systemName: "checkmark.shield.fill")
                .font(.system(size: 48))
                .foregroundStyle(.green)

            Text(loc.t("sysext_deactivated_title"))
                .font(.headline)

            Text(loc.t("sysext_deactivated_message"))
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            Button(loc.t("sysext_deactivated_reinstall")) {
                extensionState.activate()
            }
            .buttonStyle(.borderedProminent)

            Button(loc.t("sysext_deactivated_quit")) {
                NSApp.terminate(nil)
            }
            .buttonStyle(.bordered)
        }
    }

    private func extensionFailedView(_ message: String) -> some View {
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

            Button(loc.t("sysext_retry")) {
                extensionState.activate()
            }
            .buttonStyle(.borderedProminent)
        }
    }
}
