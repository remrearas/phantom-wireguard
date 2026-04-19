import Network
import NetworkExtension
import os.log

/// One TCP flow ↔ one `NWConnection`, pumped bi-directionally until
/// either side signals EOF or a hard failure. Uses "simple close"
/// semantics — when one direction ends we close the whole relay.
/// Faithfully propagates NWError to the flow on failure so the source
/// app sees the real network error rather than a synthetic reset.
///
/// The relay retains itself via the closures passed to flow/connection
/// callbacks. When `close(error:)` fires it drops those callbacks and
/// the instance deallocates naturally — no manual lifecycle wiring.
final class TCPFlowRelay {

    private let flow: NEAppProxyTCPFlow
    private let interface: NWInterface
    private let appName: String
    private var connection: NWConnection?
    private var closed = false
    private let lock = NSLock()

    /// Remote descriptor captured at `startConnection` time and reused
    /// if `close()` ever fires with an error, so the failure log names
    /// the exact host that broke.
    private var remoteDescription: String = "?"

    /// Strong self-reference kept alive for the relay's lifetime.
    /// Nothing else retains the relay — `FlowRelay.relay` creates it
    /// and returns immediately, so without this anchor the instance
    /// deallocates before `flow.open`'s async callback ever fires.
    /// `close()` nils it to let ARC reclaim the object.
    private var selfRef: TCPFlowRelay?

    private let log = OSLog(
        subsystem: "com.remrearas.Phantom-WG-MacOS.PhantomSplitTunnel",
        category: "relay.tcp"
    )

    init(flow: NEAppProxyTCPFlow, interface: NWInterface, appName: String) {
        self.flow = flow
        self.interface = interface
        self.appName = appName
    }

    // MARK: - Entry Point

    func start() {
        selfRef = self
        flow.open(withLocalEndpoint: nil) { [weak self] error in
            if let error {
                self?.close(error: error)
                return
            }
            self?.startConnection()
        }
    }

    private func startConnection() {
        guard let hostEndpoint = flow.remoteEndpoint as? NWHostEndpoint else {
            os_log("Missing remoteEndpoint", log: log, type: .error)
            close(error: nil)
            return
        }

        remoteDescription = "\(hostEndpoint.hostname):\(hostEndpoint.port)"
        let host = NWEndpoint.Host(hostEndpoint.hostname)
        let port = NWEndpoint.Port(hostEndpoint.port) ?? .any

        // Pin to the user-selected physical interface. Without this
        // the NWConnection would inherit the OS default route (utun
        // whenever a packet tunnel is active) and the "bypass" flow
        // would actually loop through the tunnel.
        let params = NWParameters.tcp
        params.requiredInterface = interface

        let conn = NWConnection(host: host, port: port, using: params)
        connection = conn

        conn.stateUpdateHandler = { [weak self] state in
            self?.handleConnectionState(state)
        }
        conn.start(queue: .global(qos: .utility))
    }

    private func handleConnectionState(_ state: NWConnection.State) {
        switch state {
        case .ready:
            pumpFlowToConnection()
            pumpConnectionToFlow()
        case .failed(let err):
            close(error: err)
        case .cancelled:
            close(error: nil)
        default:
            // .setup / .preparing / .waiting — OS is still trying.
            // No artificial timeout; matches non-VPN behaviour.
            break
        }
    }

    // MARK: - Pump Loops

    /// app → network: read from flow, write to NWConnection.
    private func pumpFlowToConnection() {
        guard !isClosed() else { return }
        flow.readData { [weak self] data, error in
            guard let self else { return }
            if let error {
                self.close(error: error)
                return
            }
            guard let data, !data.isEmpty else {
                // EOF from the app side.
                self.close(error: nil)
                return
            }
            self.connection?.send(content: data, completion: .contentProcessed { [weak self] err in
                if let err {
                    self?.close(error: err)
                    return
                }
                self?.pumpFlowToConnection()
            })
        }
    }

    /// network → app: read from NWConnection, write back into flow.
    private func pumpConnectionToFlow() {
        guard !isClosed(), let conn = connection else { return }
        conn.receive(minimumIncompleteLength: 1, maximumLength: 65_536) { [weak self] data, _, _, error in
            guard let self else { return }
            if let error {
                self.close(error: error)
                return
            }
            guard let data, !data.isEmpty else {
                // Remote closed.
                self.close(error: nil)
                return
            }
            self.flow.write(data) { [weak self] writeError in
                if let writeError {
                    self?.close(error: writeError)
                    return
                }
                self?.pumpConnectionToFlow()
            }
        }
    }

    // MARK: - Shutdown

    private func isClosed() -> Bool {
        lock.lock()
        defer { lock.unlock() }
        return closed
    }

    private func close(error: Error?) {
        lock.lock()
        if closed {
            lock.unlock()
            return
        }
        closed = true
        lock.unlock()

        if let error {
            SplitTunnelLogger.shared.log(
                "\(appName)  TCP  \(remoteDescription)  failed: \(error.localizedDescription)"
            )
        }

        flow.closeReadWithError(error)
        flow.closeWriteWithError(error)
        connection?.cancel()
        connection = nil
        selfRef = nil
    }
}
