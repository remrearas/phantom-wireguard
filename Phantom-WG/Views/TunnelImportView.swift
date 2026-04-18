import SwiftUI

/// Raw-paste import surface. The user pastes a WireGuard `.conf` (or
/// scans a QR encoding one), enters a tunnel name, and imports.
/// Structural and field-level errors are surfaced in a single inline
/// banner above the inputs — no detail form is shown here. Editing
/// individual fields is done later via `TunnelDetailView`.
struct TunnelImportView: View {
    @Environment(TunnelsManager.self) private var tunnelsManager
    @Environment(LocalizationManager.self) private var loc
    @Environment(\.dismiss) private var dismiss

    @State private var tunnelName = ""
    @State private var inputText = ""
    @State private var errorMessages: [String] = []
    @State private var showingQRScanner = false

    private var canSubmit: Bool {
        !tunnelName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        && !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if !errorMessages.isEmpty {
                    errorBanner
                }

                Form {
                    nameSection
                    rawInputSection
                    quickActionsSection
                }
            }
            .navigationTitle(loc.t("import_title"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(loc.t("cancel")) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(loc.t("import_button")) { submit() }
                        .fontWeight(.semibold)
                        .disabled(!canSubmit)
                }
            }
            .sheet(isPresented: $showingQRScanner) {
                QRScannerView { scanned in
                    showingQRScanner = false
                    inputText = scanned
                    submit()
                }
            }
        }
    }

    // MARK: - Sections

    private var nameSection: some View {
        Section {
            TextField(loc.t("import_name_placeholder"), text: $tunnelName)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
        } header: {
            Label(loc.t("import_name_section"), systemImage: "tag")
        }
    }

    private var rawInputSection: some View {
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
    }

    private var quickActionsSection: some View {
        Section {
            Button {
                showingQRScanner = true
            } label: {
                Label(loc.t("import_scan_qr"), systemImage: "qrcode.viewfinder")
            }

            Button {
                if let clipboard = UIPasteboard.general.string {
                    inputText = clipboard
                    errorMessages = []
                }
            } label: {
                Label(loc.t("import_paste"), systemImage: "doc.on.clipboard")
            }
        } header: {
            Label(loc.t("import_quick_actions"), systemImage: "bolt")
        }
    }

    // MARK: - Error Banner

    private var errorBanner: some View {
        VStack(alignment: .leading, spacing: 4) {
            ForEach(errorMessages, id: \.self) { message in
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: "exclamationmark.triangle.fill")
                    Text(message)
                        .font(.caption.weight(.medium))
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .foregroundStyle(.white)
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.red.gradient)
    }

    // MARK: - Submit

    private func submit() {
        errorMessages = []

        let trimmedName = tunnelName.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedInput = inputText.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmedName.isEmpty else {
            errorMessages = [loc.t("import_err_empty_name")]
            return
        }
        guard !trimmedInput.isEmpty else {
            errorMessages = [loc.t("parse_err_empty_input")]
            return
        }

        // Structural parse — produces a draft or throws a banner error.
        var draft: TunnelDraft
        do {
            draft = try ConfParser.parse(trimmedInput)
        } catch let error as ConfParser.ParseError {
            errorMessages = [parseErrorMessage(error)]
            return
        } catch {
            errorMessages = [error.localizedDescription]
            return
        }
        draft.name = trimmedName

        // Field-level validation — all failures are surfaced as a list
        // in the banner; the form itself never appears during import.
        let result = draft.validate()
        guard let config = result.config else {
            errorMessages = fieldErrorMessages(result.errors)
            return
        }

        Task {
            do {
                _ = try await tunnelsManager.add(config: config, activateOnDemand: .off)
                dismiss()
            } catch {
                errorMessages = [error.localizedDescription]
            }
        }
    }

    // MARK: - Error Formatting

    private func fieldErrorMessages(
        _ errors: [TunnelDraft.Field: FieldValidationError]
    ) -> [String] {
        TunnelDraft.Field.allImportOrder.compactMap { field in
            guard let error = errors[field] else { return nil }
            return "\(localizedFieldLabel(field)): \(error.localizedMessage(loc))"
        }
    }

    private func localizedFieldLabel(_ field: TunnelDraft.Field) -> String {
        switch field {
        case .name:                       return loc.t("detail_name")
        case .interfacePrivateKey:        return loc.t("detail_private_key")
        case .interfaceAddresses:         return loc.t("detail_address")
        case .interfaceDnsServers:        return loc.t("detail_dns")
        case .interfaceMTU:               return loc.t("detail_mtu")
        case .peerPublicKey:              return loc.t("detail_public_key")
        case .peerPresharedKey:           return loc.t("detail_preshared_key")
        case .peerAllowedIPs:             return loc.t("detail_allowed_ips")
        case .peerEndpoint:               return loc.t("detail_endpoint")
        case .peerPersistentKeepalive:    return loc.t("detail_keepalive")
        case .wstunnelUrl:                return loc.t("detail_server_url")
        case .wstunnelSecret:             return loc.t("detail_secret")
        case .wstunnelLocalHost:          return loc.t("detail_local_host")
        case .wstunnelLocalPort:          return loc.t("detail_local_port")
        case .wstunnelRemoteHost:         return loc.t("detail_remote_host")
        case .wstunnelRemotePort:         return loc.t("detail_remote_port")
        }
    }

    private func parseErrorMessage(_ error: ConfParser.ParseError) -> String {
        switch error {
        case .emptyInput:
            return loc.t("parse_err_empty_input")
        case .noInterfaceSection:
            return loc.t("parse_err_no_interface")
        case .noPeerSection:
            return loc.t("parse_err_no_peer")
        case .missingKey(let section, let key):
            return loc.t("parse_err_missing_key", section, key)
        case .invalidTunnelFormat(let section, let key):
            return loc.t("parse_err_invalid_tunnel", section, key)
        }
    }
}

// MARK: - Import Field Ordering

private extension TunnelDraft.Field {
    /// Stable ordering used when listing validation errors in the
    /// import banner — matches the visual order of the source `.conf`
    /// so the operator reads errors top-down.
    static var allImportOrder: [TunnelDraft.Field] {
        [
            .name,
            .wstunnelUrl, .wstunnelSecret,
            .wstunnelLocalHost, .wstunnelLocalPort,
            .wstunnelRemoteHost, .wstunnelRemotePort,
            .interfacePrivateKey, .interfaceAddresses,
            .interfaceDnsServers, .interfaceMTU,
            .peerPublicKey, .peerPresharedKey,
            .peerAllowedIPs, .peerEndpoint, .peerPersistentKeepalive
        ]
    }
}
