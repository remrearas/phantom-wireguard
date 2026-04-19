import SwiftUI

/// Inline log panel rendered inside the Split-Tunneling sheet. Polls
/// the extension's in-memory ring buffer as long as the sheet is open
/// and shows the tail in a bounded scroll view so it doesn't blow out
/// the sheet's layout. Replaces the earlier NavigationLink push, which
/// conflicted with the sheet's own toolbar on macOS.
struct SplitTunnelingLogSection: View {
    let logStore: SplitTunnelLogStore
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        Section {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 2) {
                        if logStore.entries.isEmpty {
                            Text(loc.t("log_empty_description"))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                        } else {
                            ForEach(logStore.entries) { entry in
                                entryRow(entry)
                                    .id(entry.id)
                            }
                        }
                    }
                    .padding(.vertical, 4)
                }
                .frame(height: 220)
                .background(Color(nsColor: .textBackgroundColor).opacity(0.5))
                .clipShape(RoundedRectangle(cornerRadius: 6))
                .onChange(of: logStore.entries.count) { _, _ in
                    if let last = logStore.entries.last {
                        withAnimation(.easeOut(duration: 0.15)) {
                            proxy.scrollTo(last.id, anchor: .bottom)
                        }
                    }
                }
            }
        } header: {
            Label(loc.t("detail_logs"), systemImage: "text.justify.left")
                .padding(.leading, 4)
        }
    }

    private func entryRow(_ entry: LogEntry) -> some View {
        Text(entry.text)
            .font(.system(.caption2, design: .monospaced))
            .foregroundStyle(.primary)
            .textSelection(.enabled)
            .lineLimit(nil)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 8)
    }
}
