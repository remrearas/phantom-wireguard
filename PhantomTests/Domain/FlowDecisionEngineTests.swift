import Testing
@testable import Phantom_WG_Mac

// MARK: - Self-Bypass Guard

@Suite("FlowDecisionEngine — self-bypass guard")
struct FlowDecisionEngineSelfBypassTests {

    @Test("Main app identifier is detected as self")
    func mainAppIsSelf() {
        #expect(FlowDecisionEngine.isOwnProcess(
            signingIdentifier: "9C5SL5H7CM.com.remrearas.Phantom-WG-MacOS"
        ) == true)
    }

    @Test("Tunnel extension identifier is detected as self")
    func tunnelExtensionIsSelf() {
        #expect(FlowDecisionEngine.isOwnProcess(
            signingIdentifier: "9C5SL5H7CM.com.remrearas.Phantom-WG-MacOS.PhantomTunnel"
        ) == true)
    }

    @Test("Split-tunnel extension identifier is detected as self")
    func splitTunnelExtensionIsSelf() {
        #expect(FlowDecisionEngine.isOwnProcess(
            signingIdentifier: "9C5SL5H7CM.com.remrearas.Phantom-WG-MacOS.PhantomSplitTunnel"
        ) == true)
    }

    @Test("Third-party app is NOT self")
    func thirdPartyIsNotSelf() {
        #expect(FlowDecisionEngine.isOwnProcess(
            signingIdentifier: "KL8N8XSYF4.com.brave.Browser"
        ) == false)
    }

    @Test("Apple platform-signed app is NOT self")
    func appleAppIsNotSelf() {
        #expect(FlowDecisionEngine.isOwnProcess(
            signingIdentifier: "com.apple.Safari"
        ) == false)
    }

    @Test("Different team with same bundle prefix is NOT self")
    func otherTeamSameBundlePrefixIsNotSelf() {
        // Team ID is part of the prefix — only our team qualifies.
        #expect(FlowDecisionEngine.isOwnProcess(
            signingIdentifier: "XXXXXXXXXX.com.remrearas.Phantom-WG-MacOS"
        ) == false)
    }

    @Test("Nil identifier is NOT self")
    func nilIdIsNotSelf() {
        #expect(FlowDecisionEngine.isOwnProcess(signingIdentifier: nil) == false)
    }

    @Test("Empty identifier is NOT self")
    func emptyIdIsNotSelf() {
        #expect(FlowDecisionEngine.isOwnProcess(signingIdentifier: "") == false)
    }
}

// MARK: - Matching Matrix
//
// These exercise the same helper-aware match the extension runs on
// every flow, straight from the Domain. Covers browser-helper cases
// (Brave's network service signs as `com.brave.Browser.helper`) plus
// Apple platform-signed apps, Developer-ID signed apps, and negative
// matches against unrelated bundle IDs.

private enum MatchFixture {
    /// Developer-ID signed browser — team prefix present.
    static let brave = AppEntry(
        signingIdentifier: "KL8N8XSYF4.com.brave.Browser",
        bundleIdentifier: "com.brave.Browser",
        displayName: "Brave Browser",
        teamName: "Brave Software, Inc.",
        lastKnownPath: "/Applications/Brave Browser.app"
    )

    /// Apple platform-signed — no team prefix, signingID == bundleID.
    static let safari = AppEntry(
        signingIdentifier: "com.apple.Safari",
        bundleIdentifier: "com.apple.Safari",
        displayName: "Safari",
        teamName: nil,
        lastKnownPath: "/Applications/Safari.app"
    )
}

@Suite("FlowDecisionEngine — matching (Developer-ID)")
struct FlowDecisionEngineMatchDeveloperIDTests {

    @Test("Exact signing identifier matches")
    func exactSigningIdentifier() {
        #expect(FlowDecisionEngine.matches(
            signingID: "KL8N8XSYF4.com.brave.Browser",
            against: MatchFixture.brave
        ) == true)
    }

    @Test("Child of signing identifier matches (browser helper)")
    func signingIdentifierChild() {
        #expect(FlowDecisionEngine.matches(
            signingID: "KL8N8XSYF4.com.brave.Browser.helper",
            against: MatchFixture.brave
        ) == true)
    }

    @Test("Deep child of signing identifier matches (helper variant)")
    func signingIdentifierDeepChild() {
        #expect(FlowDecisionEngine.matches(
            signingID: "KL8N8XSYF4.com.brave.Browser.helper.Renderer",
            against: MatchFixture.brave
        ) == true)
    }

    @Test("Helper without team prefix still matches via bundle namespace")
    func helperMissingTeamPrefix() {
        #expect(FlowDecisionEngine.matches(
            signingID: "com.brave.Browser.helper",
            against: MatchFixture.brave
        ) == true)
    }

    @Test("Helper with a different team prefix still matches")
    func helperDifferentTeamPrefix() {
        #expect(FlowDecisionEngine.matches(
            signingID: "ZZZZZZZZZZ.com.brave.Browser.helper",
            against: MatchFixture.brave
        ) == true)
    }

    @Test("Bare bundle identifier matches")
    func bareBundleIdentifier() {
        #expect(FlowDecisionEngine.matches(
            signingID: "com.brave.Browser",
            against: MatchFixture.brave
        ) == true)
    }

    @Test("Unrelated bundle NOT matched")
    func unrelatedBundleNotMatched() {
        #expect(FlowDecisionEngine.matches(
            signingID: "KL8N8XSYF4.com.mozilla.firefox",
            against: MatchFixture.brave
        ) == false)
    }

    @Test("Bundle that is a prefix of ours NOT matched")
    func bundlePrefixNotMatched() {
        // "com.brave" is a namespace prefix of "com.brave.Browser"
        // but the entry's bundle ID is "com.brave.Browser" — a shorter
        // ID should not greedily match via suffix/contains.
        #expect(FlowDecisionEngine.matches(
            signingID: "com.brave",
            against: MatchFixture.brave
        ) == false)
    }
}

@Suite("FlowDecisionEngine — matching (Apple platform-signed)")
struct FlowDecisionEngineMatchAppleTests {

    @Test("Exact bundle identifier matches Safari")
    func exactBundleIdentifier() {
        #expect(FlowDecisionEngine.matches(
            signingID: "com.apple.Safari",
            against: MatchFixture.safari
        ) == true)
    }

    @Test("Safari helper matches via namespace")
    func safariHelper() {
        #expect(FlowDecisionEngine.matches(
            signingID: "com.apple.Safari.SafeBrowsing.Service",
            against: MatchFixture.safari
        ) == true)
    }

    @Test("Unrelated Apple app NOT matched")
    func unrelatedApple() {
        #expect(FlowDecisionEngine.matches(
            signingID: "com.apple.Mail",
            against: MatchFixture.safari
        ) == false)
    }
}
