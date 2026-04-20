import SwiftUI
import AppKit
import UniformTypeIdentifiers

/// Inline log panel rendered inside the Split-Tunneling sheet. Polls
/// the extension's in-memory ring buffer as long as the sheet is open
/// and shows the tail in a bounded scroll view so it doesn't blow out
/// the sheet's layout. Replaces the earlier NavigationLink push, which
/// conflicted with the sheet's own toolbar on macOS.
///
/// The mini-toolbar row above the scroll surfaces the entry count and
/// Save/Clear actions — parallel to `LogView`'s toolbar for the packet
/// tunnel, scaled down to inline form.
struct SplitTunnelingLogSection: View {
    let logStore: SplitTunnelLogStore
    @Environment(LocalizationManager.self) private var loc

    @State private var savingError: String?
    @State private var showingSaveError = false

    var body: some View {
        Section {
            VStack(spacing: 8) {
                toolbar
                scrollPanel
            }
        } header: {
            Label(loc.t("detail_logs"), systemImage: "text.justify.left")
                .padding(.leading, 4)
        }
        .alert(loc.t("error"), isPresented: $showingSaveError) {
            Button(loc.t("ok")) {}
        } message: {
            Text(savingError ?? "")
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 8) {
            Text(entryCountLabel)
                .font(.caption)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 8)
                .padding(.vertical, 3)
                .background(
                    Capsule().fill(Color.secondary.opacity(0.12))
                )
                .accessibilityIdentifier(AXID.SplitTunneling.logsCount)

            Spacer(minLength: 0)

            Button {
                saveLog()
            } label: {
                Label(loc.t("log_save"), systemImage: "square.and.arrow.down")
                    .labelStyle(.iconOnly)
            }
            .buttonStyle(.borderless)
            .help(loc.t("log_save"))
            .disabled(logStore.entries.isEmpty)
            .accessibilityIdentifier(AXID.SplitTunneling.logsSave)

            Button {
                Task { await logStore.clear() }
            } label: {
                Label(loc.t("log_clear"), systemImage: "trash")
                    .labelStyle(.iconOnly)
            }
            .buttonStyle(.borderless)
            .help(loc.t("log_clear"))
            .disabled(logStore.entries.isEmpty)
            .accessibilityIdentifier(AXID.SplitTunneling.logsClear)
        }
    }

    private var entryCountLabel: String {
        let count = logStore.entries.count
        return String(format: loc.t("log_entry_count"), count)
    }

    // MARK: - Scroll Panel

    private var scrollPanel: some View {
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
            .frame(height: 240)
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

    // MARK: - Save

    private func saveLog() {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.plainText, .log]
        panel.nameFieldStringValue = defaultFilename()
        panel.canCreateDirectories = true
        panel.title = loc.t("log_save")

        guard panel.runModal() == .OK, let url = panel.url else { return }

        let contents = logStore.entries.map(\.text).joined(separator: "\n") + "\n"

        do {
            try contents.write(to: url, atomically: true, encoding: .utf8)
        } catch {
            savingError = error.localizedDescription
            showingSaveError = true
        }
    }

    private func defaultFilename() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd-HHmmss"
        return "phantom-split-log-\(formatter.string(from: Date())).txt"
    }
}
