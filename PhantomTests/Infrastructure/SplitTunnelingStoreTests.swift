import Testing
import Foundation
@testable import Phantom_WG_Mac

// MARK: - Fixtures

private enum Fixture {
    static let safari = AppEntry(
        signingIdentifier: "com.apple.Safari",
        bundleIdentifier: "com.apple.Safari",
        displayName: "Safari",
        teamName: nil,
        lastKnownPath: "/Applications/Safari.app"
    )

    static let firefox = AppEntry(
        signingIdentifier: "43AQ936H96.org.mozilla.firefox",
        bundleIdentifier: "org.mozilla.firefox",
        displayName: "Firefox",
        teamName: "Mozilla Corporation",
        lastKnownPath: "/Applications/Firefox.app"
    )

    /// Isolated on-disk URL per test — keeps the real App Group
    /// container untouched. The parent directory is created on first
    /// persist; we clean the file itself if it exists from a prior run.
    static func isolatedFileURL() -> URL {
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("phantom-split-tests", isDirectory: true)
        try? FileManager.default.createDirectory(
            at: dir,
            withIntermediateDirectories: true
        )
        let url = dir.appendingPathComponent("\(UUID().uuidString).json")
        try? FileManager.default.removeItem(at: url)
        return url
    }
}

// MARK: - First Run

@Suite("SplitTunnelingStore — first run")
@MainActor
struct SplitTunnelingStoreFirstRunTests {

    @Test("Fresh file yields the disabled baseline config")
    func freshFileIsDefault() {
        let store = SplitTunnelingStore(fileURL: Fixture.isolatedFileURL())
        #expect(store.configuration.isEnabled == false)
        #expect(store.configuration.apps.isEmpty)
        #expect(store.configuration.interfaceSelection == .auto)
    }
}

// MARK: - Mutation

@Suite("SplitTunnelingStore — mutation")
@MainActor
struct SplitTunnelingStoreMutationTests {

    @Test("setEnabled flips the gate")
    func setEnabled() {
        let store = SplitTunnelingStore(fileURL: Fixture.isolatedFileURL())
        store.setEnabled(true)
        #expect(store.configuration.isEnabled == true)
        store.setEnabled(false)
        #expect(store.configuration.isEnabled == false)
    }

    @Test("setInterfaceSelection updates the stored selection")
    func setInterfaceSelection() {
        let store = SplitTunnelingStore(fileURL: Fixture.isolatedFileURL())
        store.setInterfaceSelection(.explicit(name: "en0"))
        #expect(store.configuration.interfaceSelection == .explicit(name: "en0"))
        store.setInterfaceSelection(.auto)
        #expect(store.configuration.interfaceSelection == .auto)
    }

    @Test("addApp appends a new entry")
    func addAppAppends() {
        let store = SplitTunnelingStore(fileURL: Fixture.isolatedFileURL())
        let added = store.addApp(Fixture.safari)
        #expect(added == true)
        #expect(store.configuration.apps.count == 1)
        #expect(store.configuration.apps.first?.bundleIdentifier == "com.apple.Safari")
    }

    @Test("addApp rejects a duplicate (by bundle identifier)")
    func addAppDedup() {
        let store = SplitTunnelingStore(fileURL: Fixture.isolatedFileURL())
        _ = store.addApp(Fixture.safari)

        let duplicate = AppEntry(
            signingIdentifier: "com.apple.Safari",
            bundleIdentifier: "com.apple.Safari",
            displayName: "Impostor",
            teamName: nil,
            lastKnownPath: nil
        )
        let second = store.addApp(duplicate)
        #expect(second == false)
        #expect(store.configuration.apps.count == 1)
        #expect(store.configuration.apps.first?.displayName == "Safari")
    }

    @Test("removeApp by bundle id drops the entry")
    func removeApp() {
        let store = SplitTunnelingStore(fileURL: Fixture.isolatedFileURL())
        _ = store.addApp(Fixture.safari)
        _ = store.addApp(Fixture.firefox)
        store.removeApp(bundleIdentifier: "com.apple.Safari")
        #expect(store.configuration.apps.count == 1)
        #expect(store.configuration.apps.first?.bundleIdentifier == "org.mozilla.firefox")
    }

    @Test("reset returns to the default baseline")
    func reset() {
        let store = SplitTunnelingStore(fileURL: Fixture.isolatedFileURL())
        store.setEnabled(true)
        store.setInterfaceSelection(.explicit(name: "en1"))
        _ = store.addApp(Fixture.safari)
        _ = store.addApp(Fixture.firefox)
        store.reset()
        #expect(store.configuration == .default)
    }
}

// MARK: - Persistence

@Suite("SplitTunnelingStore — persistence round-trip")
@MainActor
struct SplitTunnelingStorePersistenceTests {

    @Test("Mutations survive across store instances")
    func persistRoundTrip() {
        let url = Fixture.isolatedFileURL()

        let first = SplitTunnelingStore(fileURL: url)
        first.setEnabled(true)
        first.setInterfaceSelection(.explicit(name: "en0"))
        _ = first.addApp(Fixture.safari)
        _ = first.addApp(Fixture.firefox)

        let second = SplitTunnelingStore(fileURL: url)
        #expect(second.configuration.isEnabled == true)
        #expect(second.configuration.interfaceSelection == .explicit(name: "en0"))
        #expect(second.configuration.apps.count == 2)
        #expect(second.configuration.apps[0].signingIdentifier == "com.apple.Safari")
        #expect(second.configuration.apps[1].signingIdentifier == "43AQ936H96.org.mozilla.firefox")
    }

    @Test("Reset clears the persisted blob")
    func resetClearsPersisted() {
        let url = Fixture.isolatedFileURL()
        let first = SplitTunnelingStore(fileURL: url)
        first.setEnabled(true)
        _ = first.addApp(Fixture.safari)
        first.reset()

        let second = SplitTunnelingStore(fileURL: url)
        #expect(second.configuration == .default)
    }
}

// MARK: - Reconcile

@Suite("SplitTunnelingStore — reconcile")
@MainActor
struct SplitTunnelingStoreReconcileTests {

    @Test("Reconcile on an empty list is a no-op")
    func reconcileEmptyNoOp() {
        let store = SplitTunnelingStore(fileURL: Fixture.isolatedFileURL())
        store.reconcile()
        #expect(store.configuration.apps.isEmpty)
    }

    // Note: full path-based reconcile (drops non-installed apps) can't
    // be safely exercised in unit tests without touching the user's
    // /Applications state. The "empty list" no-op path above is the
    // only deterministic slice; the rest is covered by the manual
    // test plan.
}
