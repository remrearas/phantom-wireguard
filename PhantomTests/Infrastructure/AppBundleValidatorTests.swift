import Testing
import Foundation
@testable import Phantom_WG_Mac

// MARK: - Helpers

private enum TestApps {
    /// Apple system apps are platform-signed (no team identifier).
    /// In the signing-identifier architecture we accept them — their
    /// code-signing identifier (`com.apple.Calculator`) is used
    /// verbatim as the `NENetworkRule(signingIdentifier:)` match key.
    static let systemCalculator = URL(fileURLWithPath: "/System/Applications/Calculator.app")

    /// Our own Developer ID signed build. Installed under /Applications
    /// by the debug post-build script; when present, this is the most
    /// reliable positive-path fixture available on the dev machine and
    /// CI runner.
    static let phantomApp = URL(fileURLWithPath: "/Applications/Phantom-WG Mac.app")

    /// Not a bundle — a plain file masquerading as a path to an app.
    static func nonBundleURL() -> URL {
        let tempDir = URL(fileURLWithPath: NSTemporaryDirectory())
        let url = tempDir.appendingPathComponent("not-a-bundle-\(UUID().uuidString).app")
        return url
    }
}

// MARK: - Tests

@Suite("AppBundleValidator — real-world bundles")
struct AppBundleValidatorRealWorldTests {

    @Test(
        "Apple system app (Calculator) is accepted with plain signing identifier",
        .enabled(if: FileManager.default.fileExists(atPath: TestApps.systemCalculator.path))
    )
    func systemAppAcceptedWithPlainIdentifier() {
        // Apple's platform-signed apps have no team id; we accept
        // them and use just the code-signing identifier (bundle id)
        // as the NENetworkRule match key. This matches the runtime
        // `flow.metaData.sourceAppSigningIdentifier` format.
        let result = AppBundleValidator.validate(url: TestApps.systemCalculator)
        switch result {
        case .success(let entry):
            #expect(entry.bundleIdentifier.hasPrefix("com.apple."))
            #expect(entry.signingIdentifier == entry.bundleIdentifier)
            #expect(!entry.displayName.isEmpty)
            #expect(entry.lastKnownPath == TestApps.systemCalculator.path)
        case .failure(let error):
            Issue.record("Expected Calculator to validate, got \(error)")
        }
    }

    @Test(
        "Our own Developer ID signed app validates end-to-end",
        .enabled(if: FileManager.default.fileExists(atPath: TestApps.phantomApp.path))
    )
    func ownAppIsValid() {
        let result = AppBundleValidator.validate(url: TestApps.phantomApp)
        switch result {
        case .success(let entry):
            #expect(entry.bundleIdentifier == "com.remrearas.Phantom-WG-MacOS")
            #expect(entry.signingIdentifier == "9C5SL5H7CM.com.remrearas.Phantom-WG-MacOS")
            #expect(!entry.displayName.isEmpty)
            #expect(entry.lastKnownPath == TestApps.phantomApp.path)
        case .failure(let error):
            Issue.record("Expected Phantom-WG Mac to validate, got \(error)")
        }
    }
}

@Suite("AppBundleValidator — rejection paths")
struct AppBundleValidatorRejectionTests {

    @Test("Non-existent path → notABundle")
    func nonExistentPath() {
        let url = TestApps.nonBundleURL()
        let result = AppBundleValidator.validate(url: url)
        switch result {
        case .success:
            Issue.record("Expected failure for missing path")
        case .failure(let error):
            #expect(error == .notABundle)
        }
    }
}
