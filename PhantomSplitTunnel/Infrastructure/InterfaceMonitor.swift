import Foundation
import Network

/// Extension-local interface watcher. Runs in the PhantomSplitTunnel
/// process, tracks the currently available non-tunnel interfaces,
/// resolves the user's `InterfaceSelection`, and signals when the
/// selected interface vanishes so the proxy can cancel itself.
final class InterfaceMonitor {

    /// Called whenever the currently-resolved interface changes. `nil`
    /// means no valid interface is available — e.g. the user's chosen
    /// Ethernet cable was pulled and there's no Wi-Fi fallback.
    var onChange: ((NWInterface?) -> Void)?

    private(set) var current: NWInterface?

    private var selection: InterfaceSelection = .auto
    private var available: [NWInterface] = []

    private let monitor = NWPathMonitor(prohibitedInterfaceTypes: [.other, .loopback])
    private let queue = DispatchQueue(
        label: "com.remrearas.Phantom-WG-MacOS.PhantomSplitTunnel.interface-monitor",
        qos: .utility
    )
    private let syncQueue = DispatchQueue(
        label: "com.remrearas.Phantom-WG-MacOS.PhantomSplitTunnel.interface-monitor.sync"
    )

    // MARK: - Lifecycle

    func start() {
        monitor.pathUpdateHandler = { [weak self] path in
            self?.syncQueue.async {
                self?.apply(availableInterfaces: path.availableInterfaces)
            }
        }
        monitor.start(queue: queue)
    }

    func stop() {
        monitor.cancel()
    }

    // MARK: - Selection

    /// Called from `startProxy` and reload (opcode 0x00).
    func setSelection(_ selection: InterfaceSelection) {
        syncQueue.async { [weak self] in
            self?.selection = selection
            self?.resolve()
        }
    }

    // MARK: - Private

    private func apply(availableInterfaces: [NWInterface]) {
        // Dedupe — a single NIC often appears across address families.
        var seen = Set<String>()
        available = availableInterfaces.filter { seen.insert($0.name).inserted }
        resolve()
    }

    /// Selects the interface that matches the stored `InterfaceSelection`
    /// and notifies the delegate. Emits `nil` when the explicit name
    /// can't be found among available interfaces so the caller can stop
    /// the session with a useful error.
    private func resolve() {
        let resolved: NWInterface?
        switch selection {
        case .auto:
            resolved = available.first(where: { $0.type == .wiredEthernet })
                ?? available.first(where: { $0.type == .wifi })
                ?? available.first
        case .explicit(let name):
            resolved = available.first(where: { $0.name == name })
        }

        let previous = current
        current = resolved

        if previous?.name != resolved?.name {
            onChange?(resolved)
        }
    }
}
