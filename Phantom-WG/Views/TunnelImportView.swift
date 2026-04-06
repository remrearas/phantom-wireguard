import SwiftUI

struct TunnelImportView: View {
    @EnvironmentObject var tunnelsManager: TunnelsManager
    @EnvironmentObject var loc: LocalizationManager
    @Environment(\.dismiss) private var dismiss

    @State private var tunnelName = ""
    @State private var inputText = ""
    @State private var errorMessage: String?
    @State private var showingQRScanner = false

    private var canSubmit: Bool {
        !tunnelName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        && !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if let error = errorMessage {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                        Text(error)
                            .font(.caption.weight(.medium))
                    }
                    .foregroundStyle(.white)
                    .padding(12)
                    .frame(maxWidth: .infinity)
                    .background(.red.gradient)
                }

                Form {
                    Section {
                        TextField(loc.t("import_name_placeholder"), text: $tunnelName)
                            .autocorrectionDisabled()
                            .textInputAutocapitalization(.never)
                    } header: {
                        Label(loc.t("import_name_section"), systemImage: "tag")
                    }

                    Section {
                        TextEditor(text: $inputText)
                            .font(.system(.caption, design: .monospaced))
                            .frame(minHeight: 150)
                            .autocorrectionDisabled()
                            .textInputAutocapitalization(.never)
                    } header: {
                        Label(loc.t("import_configuration"), systemImage: "doc.text")
                    } footer: {
                        Text(loc.t("import_footer"))
                    }

                    Section {
                        Button {
                            showingQRScanner = true
                        } label: {
                            Label(loc.t("import_scan_qr"), systemImage: "qrcode.viewfinder")
                        }

                        Button {
                            if let clipboard = UIPasteboard.general.string {
                                inputText = clipboard
                                errorMessage = nil
                            }
                        } label: {
                            Label(loc.t("import_paste"), systemImage: "doc.on.clipboard")
                        }
                    } header: {
                        Label(loc.t("import_quick_actions"), systemImage: "bolt")
                    }
                }
            }
            .navigationTitle(loc.t("import_title"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(loc.t("cancel")) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(loc.t("import_button")) { importConfig() }
                        .fontWeight(.semibold)
                        .disabled(!canSubmit)
                }
            }
            .sheet(isPresented: $showingQRScanner) {
                QRScannerView { scanned in
                    showingQRScanner = false
                    inputText = scanned
                    importConfig()
                }
            }
        }
    }

    private func importConfig() {
        let trimmed = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        let name = tunnelName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !name.isEmpty else { return }

        do {
            var config = try ConfParser.parse(trimmed)
            config.name = name
            config = try config.validated()

            Task {
                do {
                    _ = try await tunnelsManager.add(config: config, activateOnDemand: .off)
                    dismiss()
                } catch {
                    errorMessage = error.localizedDescription
                }
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
