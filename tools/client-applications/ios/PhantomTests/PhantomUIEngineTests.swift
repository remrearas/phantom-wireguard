import Foundation
import SwiftUI
import Testing
@testable import Phantom_WG

// ═══════════════════════════════════════════════════════════
// MARK: - PhantomUIEngine Senaryo Testleri
//         PhantomUIEngine Scenario Tests
// ═══════════════════════════════════════════════════════════
//
// Connection detaylarına bağımlı olmadan, yalnızca TunnelStatus enum
// değerleri üzerinden UI kurallarını doğrular.
//
// Validates UI rules purely through TunnelStatus enum values,
// without any dependency on connection details.

/// Tüm olası tunnel durumları — parametreli testlerde kullanılır.
/// All possible tunnel statuses — used in parameterized tests.
let allStatuses: [TunnelStatus] = [
    .inactive, .activating, .active, .deactivating, .reasserting, .restarting, .waiting
]

// ─────────────────────────────────────────────────────────
// MARK: - A. Etkileşim Kuralları / Interaction Rules
// ─────────────────────────────────────────────────────────

@Suite("A. Etkileşim Kuralları / Interaction Rules")
struct InteractionRuleTests {

    @Test("canEditConfig — yalnızca inactive'de true döner",
          arguments: allStatuses)
    func canEditConfig(status: TunnelStatus) {
        let result = PhantomUIEngine.canEditConfig(status: status)
        #expect(result == (status == .inactive))
    }

    @Test("canDeleteTunnel — yalnızca inactive'de true döner",
          arguments: allStatuses)
    func canDeleteTunnel(status: TunnelStatus) {
        let result = PhantomUIEngine.canDeleteTunnel(status: status)
        #expect(result == (status == .inactive))
    }

    @Test("canModifyTunnelList — senaryolar")
    func canModifyTunnelList() {
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.inactive, .inactive]) == true)
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: []) == true)
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.inactive, .active]) == false)
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.inactive, .activating]) == false)
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.inactive, .deactivating]) == false)
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.inactive, .waiting]) == false)
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.inactive]) == true)
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.active]) == false)
    }

    @Test("canSubmitImport — boş ve dolu text kontrolleri")
    func canSubmitImport() {
        #expect(PhantomUIEngine.canSubmitImport(text: "") == false)
        #expect(PhantomUIEngine.canSubmitImport(text: "   ") == false)
        #expect(PhantomUIEngine.canSubmitImport(text: "\n\t") == false)
        #expect(PhantomUIEngine.canSubmitImport(text: "{ \"name\": \"test\" }") == true)
        #expect(PhantomUIEngine.canSubmitImport(text: "x") == true)
    }
}

// ─────────────────────────────────────────────────────────
// MARK: - B. Görünürlük Kuralları / Visibility Rules
// ─────────────────────────────────────────────────────────

@Suite("B. Görünürlük Kuralları / Visibility Rules")
struct VisibilityRuleTests {

    @Test("shouldShowStats — inactive hariç hepsinde true",
          arguments: allStatuses)
    func shouldShowStats(status: TunnelStatus) {
        let result = PhantomUIEngine.shouldShowStats(status: status)
        #expect(result == (status != .inactive))
    }

    @Test("shouldShowActivationError — nil ve non-nil kontrolleri")
    func shouldShowActivationError() {
        #expect(PhantomUIEngine.shouldShowActivationError(nil) == false)

        let error = TunnelActivationError.startingFailed(
            systemError: NSError(domain: "test", code: 0)
        )
        #expect(PhantomUIEngine.shouldShowActivationError(error) == true)
    }
}

// ─────────────────────────────────────────────────────────
// MARK: - C. Görsel Kuralları / Appearance Rules
// ─────────────────────────────────────────────────────────

@Suite("C. Görsel Kuralları / Appearance Rules")
struct AppearanceRuleTests {

    @Test("statusColor — renk eşleme tablosu")
    func statusColor() {
        #expect(PhantomUIEngine.statusColor(for: .active) == .green)
        #expect(PhantomUIEngine.statusColor(for: .activating) == .orange)
        #expect(PhantomUIEngine.statusColor(for: .waiting) == .orange)
        #expect(PhantomUIEngine.statusColor(for: .reasserting) == .orange)
        #expect(PhantomUIEngine.statusColor(for: .restarting) == .orange)
        #expect(PhantomUIEngine.statusColor(for: .deactivating) == .orange)
        #expect(PhantomUIEngine.statusColor(for: .inactive) == .secondary)
    }

    @Test("statusIcon — ikon eşleme tablosu")
    func statusIcon() {
        #expect(PhantomUIEngine.statusIcon(for: .active) == "shield.checkered")
        #expect(PhantomUIEngine.statusIcon(for: .activating) == "arrow.triangle.2.circlepath")
        #expect(PhantomUIEngine.statusIcon(for: .waiting) == "arrow.triangle.2.circlepath")
        #expect(PhantomUIEngine.statusIcon(for: .reasserting) == "arrow.triangle.2.circlepath")
        #expect(PhantomUIEngine.statusIcon(for: .restarting) == "arrow.triangle.2.circlepath")
        #expect(PhantomUIEngine.statusIcon(for: .deactivating) == "arrow.down.circle")
        #expect(PhantomUIEngine.statusIcon(for: .inactive) == "shield.slash")
    }

    @Test("fieldForegroundStyle — status'a göre renk",
          arguments: allStatuses)
    func fieldForegroundStyle(status: TunnelStatus) {
        let result = PhantomUIEngine.fieldForegroundStyle(status: status)
        let expected: Color = status == .inactive ? .primary : .secondary
        #expect(result == expected)
    }

    @Test("logTagColor — tag → renk eşlemesi")
    func logTagColor() {
        #expect(PhantomUIEngine.logTagColor("WS") == .orange)
        #expect(PhantomUIEngine.logTagColor("WG") == .green)
        #expect(PhantomUIEngine.logTagColor("TUN") == .blue)
        #expect(PhantomUIEngine.logTagColor("UNKNOWN") == .secondary)
        #expect(PhantomUIEngine.logTagColor("") == .secondary)
    }
}

// ─────────────────────────────────────────────────────────
// MARK: - D. Davranış Kuralları / Behavior Rules
// ─────────────────────────────────────────────────────────

@Suite("D. Davranış Kuralları / Behavior Rules")
struct BehaviorRuleTests {

    @Test("shouldAutoSave — status × hasChanges matrisi",
          arguments: allStatuses)
    func shouldAutoSave(status: TunnelStatus) {
        #expect(PhantomUIEngine.shouldAutoSave(status: status, hasChanges: false) == false)

        let expected = (status == .inactive)
        #expect(PhantomUIEngine.shouldAutoSave(status: status, hasChanges: true) == expected)
    }

    @Test("isToggleOn — status'a göre ON/OFF",
          arguments: allStatuses)
    func isToggleOn(status: TunnelStatus) {
        let result = PhantomUIEngine.isToggleOn(status: status)
        let expectedOn: Set<TunnelStatus> = [.active, .activating, .waiting, .reasserting, .restarting]
        #expect(result == expectedOn.contains(status))
    }
}

// ─────────────────────────────────────────────────────────
// MARK: - Ç. Çapraz Senaryolar / Cross-Scenario Tests
// ─────────────────────────────────────────────────────────

@Suite("Ç. Çapraz Senaryolar / Cross-Scenario Tests")
struct CrossScenarioTests {

    @Test("Senaryo B — Tunnel aktifken tüm edit/delete engellenir")
    func scenarioB_tunnelActive() {
        let status = TunnelStatus.active
        #expect(PhantomUIEngine.canEditConfig(status: status) == false)
        #expect(PhantomUIEngine.canDeleteTunnel(status: status) == false)
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [status]) == false)
        #expect(PhantomUIEngine.shouldShowStats(status: status) == true)
        #expect(PhantomUIEngine.isToggleOn(status: status) == true)
        #expect(PhantomUIEngine.shouldAutoSave(status: status, hasChanges: true) == false)
        #expect(PhantomUIEngine.fieldForegroundStyle(status: status) == .secondary)
    }

    @Test("Senaryo C — Tunnel inaktifken tüm işlemler açık")
    func scenarioC_tunnelInactive() {
        let status = TunnelStatus.inactive
        #expect(PhantomUIEngine.canEditConfig(status: status) == true)
        #expect(PhantomUIEngine.canDeleteTunnel(status: status) == true)
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [status]) == true)
        #expect(PhantomUIEngine.shouldShowStats(status: status) == false)
        #expect(PhantomUIEngine.isToggleOn(status: status) == false)
        #expect(PhantomUIEngine.shouldAutoSave(status: status, hasChanges: true) == true)
        #expect(PhantomUIEngine.fieldForegroundStyle(status: status) == .primary)
    }

    @Test("Senaryo D — Waiting durumunda kurallar")
    func scenarioD_tunnelWaiting() {
        let status = TunnelStatus.waiting
        #expect(PhantomUIEngine.canEditConfig(status: status) == false)
        #expect(PhantomUIEngine.canDeleteTunnel(status: status) == false)
        #expect(PhantomUIEngine.isToggleOn(status: status) == true)
        #expect(PhantomUIEngine.shouldShowStats(status: status) == true)
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.active, .waiting]) == false)
    }
}
