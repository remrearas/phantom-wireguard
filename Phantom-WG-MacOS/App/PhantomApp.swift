import SwiftUI
import AppKit

@main
struct PhantomApp: App {

    /// Skips system extension activation in the test environment.
    static var isRunningTests: Bool {
        ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] != nil
    }

    @State private var extensionState = SystemExtensionState()
    @State private var splitExtensionState = SplitTunnelExtensionState()
    @State private var tunnelsManager = TunnelsManagerLoader()
    @State private var loc = LocalizationManager.shared
    @State private var splitTunnelingStore = SplitTunnelingStore()

    var body: some Scene {
        WindowGroup {
            Group {
                switch extensionState.status {
                case .unknown, .activating:
                    ActivatingView()

                case .needsApproval:
                    ApprovalView(
                        onOpenSettings: openSystemSettings,
                        onCheckAgain: extensionState.activate
                    )

                case .activated:
                    TunnelContentView(loader: tunnelsManager)

                case .deactivated:
                    DeactivatedView(onReinstall: extensionState.activate)

                case .failed(let message):
                    FailedView(message: message, onRetry: extensionState.activate)
                }
            }
            .environment(loc)
            .environment(extensionState)
            .environment(splitExtensionState)
            .environment(splitTunnelingStore)
            .tint(Color.accentColor)
            .frame(width: 480, height: 720)
            .onAppear {
                // Prune split tunneling entries whose apps are no longer
                // installed before any user interaction — keeps the list
                // in sync with what LaunchServices currently resolves.
                splitTunnelingStore.reconcile()

                guard !PhantomApp.isRunningTests else {
                    extensionState.status = .activated
                    return
                }
                extensionState.activate()
            }
        }
        .windowResizability(.contentSize)
    }

    /// Opens the correct System Settings pane for the current macOS —
    /// Sequoia moved network extensions under Login Items & Extensions;
    /// Sonoma still uses Privacy & Security → Extensions.
    private func openSystemSettings() {
        if #available(macOS 15.0, *) {
            NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.LoginItems-Settings.extension")!)
        } else {
            NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles")!)
        }
    }
}
