import SwiftUI

/// WireGuard interface configuration — private key, local addresses,
/// DNS servers, and MTU. Editable only while the tunnel is inactive.
struct InterfaceSection: View {
    @Binding var draft: InterfaceDraft
    let isEditable: Bool
    let fieldErrors: [TunnelDraft.Field: FieldValidationError]
    @Environment(LocalizationManager.self) private var loc

    var body: some View {
        Section {
            PhantomTextField(
                label: loc.t("detail_private_key"),
                text: $draft.privateKey,
                isDisabled: !isEditable,
                errorMessage: fieldErrors[.interfacePrivateKey]?.localizedMessage(loc),
                axIdentifier: AXID.TunnelDetail.Interface.privateKey
            )
            PhantomTextField(
                label: loc.t("detail_address"),
                text: $draft.addresses,
                isDisabled: !isEditable,
                errorMessage: fieldErrors[.interfaceAddresses]?.localizedMessage(loc),
                axIdentifier: AXID.TunnelDetail.Interface.addresses
            )
            PhantomTextField(
                label: loc.t("detail_dns"),
                text: $draft.dnsServers,
                isDisabled: !isEditable,
                errorMessage: fieldErrors[.interfaceDnsServers]?.localizedMessage(loc),
                axIdentifier: AXID.TunnelDetail.Interface.dnsServers
            )
            PhantomStringNumericField(
                label: loc.t("detail_mtu"),
                text: $draft.mtu,
                isDisabled: !isEditable,
                errorMessage: fieldErrors[.interfaceMTU]?.localizedMessage(loc),
                axIdentifier: AXID.TunnelDetail.Interface.mtu
            )
        } header: {
            Label(loc.t("detail_interface"), systemImage: "rectangle.connected.to.line.below")
        }
    }
}
