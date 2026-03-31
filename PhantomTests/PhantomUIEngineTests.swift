import Foundation
import SwiftUI
import Testing
@testable import Phantom_WG_Mac

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
//
// Akış diyagramları / Flow diagrams: TEST_FLOWS.md

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

    /// A1: Config yalnızca inactive iken edit edilebilir.
    /// A1: Config can only be edited when inactive.
    @Test("canEditConfig — yalnızca inactive'de true döner",
          arguments: allStatuses)
    func canEditConfig(status: TunnelStatus) {
        let result = PhantomUIEngine.canEditConfig(status: status)
        #expect(result == (status == .inactive))
    }

    /// A2: Tunnel yalnızca inactive iken silinebilir.
    /// A2: Tunnel can only be deleted when inactive.
    @Test("canDeleteTunnel — yalnızca inactive'de true döner",
          arguments: allStatuses)
    func canDeleteTunnel(status: TunnelStatus) {
        let result = PhantomUIEngine.canDeleteTunnel(status: status)
        #expect(result == (status == .inactive))
    }

    /// A3/A4/A5: Tüm tunnel'lar inactive iken liste değiştirilebilir.
    /// A3/A4/A5: List can be modified only when all tunnels are inactive.
    @Test("canModifyTunnelList — senaryolar")
    func canModifyTunnelList() {
        // Tüm inactive → izin ver
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.inactive, .inactive]) == true)

        // Boş liste → izin ver
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: []) == true)

        // Bir tanesi active → engelle
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.inactive, .active]) == false)

        // Bir tanesi activating → engelle
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.inactive, .activating]) == false)

        // Bir tanesi deactivating → engelle
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.inactive, .deactivating]) == false)

        // Bir tanesi waiting → engelle
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.inactive, .waiting]) == false)

        // Tek tunnel, inactive → izin ver
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.inactive]) == true)

        // Tek tunnel, active → engelle
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.active]) == false)
    }

    /// A6: Toggle disabled when another tunnel is active.
    @Test("canToggleTunnel — scenarios")
    func canToggleTunnel() {
        // This tunnel inactive, no others active → can toggle
        #expect(PhantomUIEngine.canToggleTunnel(tunnelStatus: .inactive, allStatuses: [.inactive, .inactive]) == true)

        // This tunnel inactive, another active → cannot toggle
        #expect(PhantomUIEngine.canToggleTunnel(tunnelStatus: .inactive, allStatuses: [.inactive, .active]) == false)

        // This tunnel active, it's the one that's active → can toggle (to deactivate)
        #expect(PhantomUIEngine.canToggleTunnel(tunnelStatus: .active, allStatuses: [.active, .inactive]) == true)

        // This tunnel inactive, another activating → cannot toggle
        #expect(PhantomUIEngine.canToggleTunnel(tunnelStatus: .inactive, allStatuses: [.inactive, .activating]) == false)

        // Single tunnel, inactive → can toggle
        #expect(PhantomUIEngine.canToggleTunnel(tunnelStatus: .inactive, allStatuses: [.inactive]) == true)

        // Empty list → can toggle
        #expect(PhantomUIEngine.canToggleTunnel(tunnelStatus: .inactive, allStatuses: []) == true)
    }

    /// A7: Maximum tunnel limit.
    @Test("maxTunnels — constant is 5")
    func maxTunnels() {
        #expect(PhantomUIEngine.maxTunnels == 5)
    }

    /// A8: Cannot add tunnel when limit reached or any tunnel is active.
    @Test("canAddTunnel — scenarios")
    func canAddTunnel() {
        // Under limit, all inactive → can add
        #expect(PhantomUIEngine.canAddTunnel(tunnelCount: 3, statuses: [.inactive, .inactive, .inactive]) == true)

        // At limit, all inactive → cannot add
        #expect(PhantomUIEngine.canAddTunnel(tunnelCount: 5, statuses: [.inactive, .inactive, .inactive, .inactive, .inactive]) == false)

        // Under limit, one active → cannot add
        #expect(PhantomUIEngine.canAddTunnel(tunnelCount: 2, statuses: [.inactive, .active]) == false)

        // Empty → can add
        #expect(PhantomUIEngine.canAddTunnel(tunnelCount: 0, statuses: []) == true)

        // Over limit (edge case) → cannot add
        #expect(PhantomUIEngine.canAddTunnel(tunnelCount: 6, statuses: [.inactive]) == false)
    }

    /// A9: Cannot import with empty text.
    @Test("canSubmitImport — empty and non-empty text checks")
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

    /// B1: Stats section yalnızca inactive olmadığında görünür.
    /// B1: Stats section is visible only when not inactive.
    @Test("shouldShowStats — inactive hariç hepsinde true",
          arguments: allStatuses)
    func shouldShowStats(status: TunnelStatus) {
        let result = PhantomUIEngine.shouldShowStats(status: status)
        #expect(result == (status != .inactive))
    }

    /// B2: Hata metni yalnızca error varsa görünür.
    /// B2: Error text is visible only when an error exists.
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

    /// C1: Her status için beklenen renk doğru mu?
    /// C1: Is the expected color correct for each status?
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

    /// C2: Her status için beklenen SF Symbol ikonu doğru mu?
    /// C2: Is the expected SF Symbol icon correct for each status?
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

    /// C3: Field foreground stili — inactive'de primary, diğerlerinde secondary.
    /// C3: Field foreground style — primary when inactive, secondary otherwise.
    @Test("fieldForegroundStyle — status'a göre renk",
          arguments: allStatuses)
    func fieldForegroundStyle(status: TunnelStatus) {
        let result = PhantomUIEngine.fieldForegroundStyle(status: status)
        let expected: Color = status == .inactive ? .primary : .secondary
        #expect(result == expected)
    }

    /// C4: Log tag renk eşlemesi.
    /// C4: Log tag color mapping.
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

    /// D1: Auto-save yalnızca inactive + değişiklik varsa tetiklenir.
    /// D1: Auto-save triggers only when inactive + changes exist.
    @Test("shouldAutoSave — status × hasChanges matrisi",
          arguments: allStatuses)
    func shouldAutoSave(status: TunnelStatus) {
        // Değişiklik yok → hiçbir zaman auto-save yok
        #expect(PhantomUIEngine.shouldAutoSave(status: status, hasChanges: false) == false)

        // Değişiklik var → yalnızca inactive'de true
        let expected = (status == .inactive)
        #expect(PhantomUIEngine.shouldAutoSave(status: status, hasChanges: true) == expected)
    }

    /// D5: Toggle ON durumu — active/activating/waiting/reasserting/restarting'de ON.
    /// D5: Toggle ON state — ON for active/activating/waiting/reasserting/restarting.
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

    /// Senaryo B: Tunnel bağlandığında UI kuralları tutarlı mı?
    /// Scenario B: Are UI rules consistent when tunnel connects?
    @Test("Senaryo B — Tunnel aktifken tüm edit/delete engellenir")
    func scenarioB_tunnelActive() {
        let status = TunnelStatus.active

        // Config edit edilemez
        #expect(PhantomUIEngine.canEditConfig(status: status) == false)

        // Tunnel silinemez
        #expect(PhantomUIEngine.canDeleteTunnel(status: status) == false)

        // Liste değiştirilemez (import/swipe-delete)
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [status]) == false)

        // Stats görünür
        #expect(PhantomUIEngine.shouldShowStats(status: status) == true)

        // Toggle ON
        #expect(PhantomUIEngine.isToggleOn(status: status) == true)

        // Auto-save tetiklenmez (değişiklik olsa bile)
        #expect(PhantomUIEngine.shouldAutoSave(status: status, hasChanges: true) == false)

        // Field stili secondary (disabled görünümü)
        #expect(PhantomUIEngine.fieldForegroundStyle(status: status) == .secondary)

        // Other tunnels' toggles disabled
        #expect(PhantomUIEngine.canToggleTunnel(tunnelStatus: .inactive, allStatuses: [.inactive, status]) == false)

        // Cannot add new tunnel while active
        #expect(PhantomUIEngine.canAddTunnel(tunnelCount: 1, statuses: [status]) == false)
    }

    /// Senaryo C: Tunnel inaktifken tüm işlemler açık mı?
    /// Scenario C: Are all operations enabled when tunnel is inactive?
    @Test("Senaryo C — Tunnel inaktifken tüm işlemler açık")
    func scenarioC_tunnelInactive() {
        let status = TunnelStatus.inactive

        // Config edit edilebilir
        #expect(PhantomUIEngine.canEditConfig(status: status) == true)

        // Tunnel silinebilir
        #expect(PhantomUIEngine.canDeleteTunnel(status: status) == true)

        // Liste değiştirilebilir
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [status]) == true)

        // Stats gizli
        #expect(PhantomUIEngine.shouldShowStats(status: status) == false)

        // Toggle OFF
        #expect(PhantomUIEngine.isToggleOn(status: status) == false)

        // Auto-save tetiklenir (değişiklik varsa)
        #expect(PhantomUIEngine.shouldAutoSave(status: status, hasChanges: true) == true)

        // Field stili primary (editable görünümü)
        #expect(PhantomUIEngine.fieldForegroundStyle(status: status) == .primary)

        // Toggle enabled when all inactive
        #expect(PhantomUIEngine.canToggleTunnel(tunnelStatus: status, allStatuses: [status]) == true)

        // Can add new tunnel when inactive and under limit
        #expect(PhantomUIEngine.canAddTunnel(tunnelCount: 1, statuses: [status]) == true)
    }

    /// Senaryo D: Tunnel değiştirme — waiting durumunda kurallar.
    /// Scenario D: Tunnel switching — rules during waiting state.
    @Test("Senaryo D — Waiting durumunda kurallar")
    func scenarioD_tunnelWaiting() {
        let status = TunnelStatus.waiting

        // Edit/delete engellenir
        #expect(PhantomUIEngine.canEditConfig(status: status) == false)
        #expect(PhantomUIEngine.canDeleteTunnel(status: status) == false)

        // Toggle ON (waiting = aktif sayılır)
        #expect(PhantomUIEngine.isToggleOn(status: status) == true)

        // Stats görünür
        #expect(PhantomUIEngine.shouldShowStats(status: status) == true)

        // Liste mixed: bir active + bir waiting → değiştirilemez
        #expect(PhantomUIEngine.canModifyTunnelList(statuses: [.active, .waiting]) == false)
    }
}
