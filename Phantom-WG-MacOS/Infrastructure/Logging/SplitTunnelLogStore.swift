import Foundation
import Observation

/// Polls the `PhantomSplitTunnel` extension for its in-memory log
/// buffer and exposes the lines as `LogEntry` rows that `LogView` can
/// render alongside the tunnel's structured logs.
///
/// The extension ships a newline-delimited string; we parse each line
/// and lift it into the shared `LogEntry` shape (using "SPL" as the
/// tag). No parsing beyond line splitting — messages already carry
/// their ISO-8601 timestamp as produced by `SplitTunnelLogger`.
@Observable
@MainActor
final class SplitTunnelLogStore: LogEntryProvider {

    var entries: [LogEntry] = []

    @ObservationIgnored private weak var providerManager: SplitTunnelProviderManager?
    @ObservationIgnored private var pollingTask: Task<Void, Never>?

    init(providerManager: SplitTunnelProviderManager) {
        self.providerManager = providerManager
    }

    func startPolling() {
        guard pollingTask == nil else { return }
        pollingTask = Task { [weak self] in
            while !Task.isCancelled {
                do {
                    try await Task.sleep(for: .seconds(1))
                } catch {
                    break
                }
                await self?.fetchLogs()
            }
        }
    }

    func stopPolling() {
        pollingTask?.cancel()
        pollingTask = nil
    }

    // MARK: - Private

    private func fetchLogs() async {
        guard let providerManager,
              let dump = await providerManager.fetchLogs(),
              !dump.isEmpty else {
            if !entries.isEmpty { entries.removeAll() }
            return
        }

        entries = dump
            .split(separator: "\n", omittingEmptySubsequences: true)
            .enumerated()
            .map { index, line in
                LogEntry(
                    id: index,
                    tag: "SPL",
                    timestamp: "",
                    text: String(line)
                )
            }
    }
}
