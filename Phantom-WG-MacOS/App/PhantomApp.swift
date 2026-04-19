import SwiftUI
import AppKit

@main
@MainActor
struct PhantomApp: App {

    /// Skips system extension activation in the test environment.
    static var isRunningTests: Bool {
        ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] != nil
    }

    @State private var extensionState: SystemExtensionState
    @State private var splitExtensionState: SplitTunnelExtensionState
    @State private var tunnelsManager: TunnelsManagerLoader
    @State private var loc: LocalizationManager
    @State private var splitTunnelingStore: SplitTunnelingStore
    @State private var splitProviderManager: SplitTunnelProviderManager
    @State private var interfaceResolver: PhysicalInterfaceResolver
    @State private var toastCenter: ToastCenter

    init() {
        let loc = LocalizationManager.shared
        let extensionState = SystemExtensionState()
        let splitExtensionState = SplitTunnelExtensionState()
        let tunnelsManager = TunnelsManagerLoader()
        let splitTunnelingStore = SplitTunnelingStore()
        let splitProviderManager = SplitTunnelProviderManager()
        splitTunnelingStore.providerManager = splitProviderManager

        _loc = State(initialValue: loc)
        _extensionState = State(initialValue: extensionState)
        _splitExtensionState = State(initialValue: splitExtensionState)
        _tunnelsManager = State(initialValue: tunnelsManager)
        _splitTunnelingStore = State(initialValue: splitTunnelingStore)
        _splitProviderManager = State(initialValue: splitProviderManager)
        _interfaceResolver = State(initialValue: PhysicalInterfaceResolver())
        _toastCenter = State(initialValue: ToastCenter())
    }

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
            .environment(splitProviderManager)
            .environment(interfaceResolver)
            .environment(toastCenter)
            .tint(Color.accentColor)
            .frame(width: 480, height: 720)
            .onAppear {
                splitTunnelingStore.reconcile()
                interfaceResolver.start()
                Task { await splitProviderManager.load() }

                guard !PhantomApp.isRunningTests else {
                    extensionState.status = .activated
                    return
                }
                extensionState.activate()
            }
            .onChange(of: splitTunnelingStore.configuration.isEnabled) { _, _ in
                reconcileSplitSession()
            }
            .onChange(of: splitExtensionState.status) { _, _ in
                reconcileSplitSession()
            }
        }
        .windowResizability(.contentSize)
    }

    // MARK: - Split-Tunnel Session Reconciliation

    /// The split-tunnel extension runs on a single, independent
    /// condition: "user wants it on AND the extension is installed."
    /// The packet-tunnel's state doesn't feed in — each extension has
    /// its own lifecycle. Bypass flows are pinned to the user-selected
    /// physical interface by the extension itself.
    private func reconcileSplitSession() {
        let shouldRun = splitTunnelingStore.configuration.isEnabled
            && splitExtensionState.status == .activated

        let currentConfig = splitTunnelingStore.configuration
        Task { @MainActor in
            switch (shouldRun, splitProviderManager.sessionStatus) {
            case (true, .disconnected), (true, .invalid):
                try? await splitProviderManager.enable(with: currentConfig)
            case (false, .connected), (false, .connecting):
                try? await splitProviderManager.disable()
            default:
                break
            }
        }
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
