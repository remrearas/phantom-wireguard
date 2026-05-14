import Foundation
import Network

/// Shared `NWPathMonitor` watcher of physical interfaces. Both system
/// extensions instantiate their own copy; each binary embeds this
/// source via the project source-list. Filters `.other` and
/// `.loopback` so utun and synthetic interfaces never become
/// candidates; resolves the user's `InterfaceSelection`; fires
/// `onChange` whenever the resolved interface (including `nil`)
/// changes.
final class InterfaceMonitor {

    /// `nil` means no valid interface is available — the caller's
    /// strict reject path kicks in.
    var onChange: ((NWInterface?) -> Void)?

    private(set) var current: NWInterface?

    private var selection: InterfaceSelection = .auto
    private var available: [NWInterface] = []

    private let monitor = NWPathMonitor(prohibitedInterfaceTypes: [.other, .loopback])
    private let queue = DispatchQueue(
        label: "com.remrearas.Phantom-WG-MacOS.interface-monitor",
        qos: .utility
    )
    private let syncQueue = DispatchQueue(
        label: "com.remrearas.Phantom-WG-MacOS.interface-monitor.sync"
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

    func setSelection(_ selection: InterfaceSelection) {
        syncQueue.async { [weak self] in
            self?.selection = selection
            self?.resolve()
        }
    }

    // MARK: - Private

    private func apply(availableInterfaces: [NWInterface]) {
        // Dedupe — a NIC can appear across address families.
        var seen = Set<String>()
        available = availableInterfaces.filter { seen.insert($0.name).inserted }
        resolve()
    }

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
