import Foundation

// MARK: - Flow Decision Engine

/// Collapsed to a single helper in the signing-identifier-based
/// architecture: the OS now filters flows via
/// `NENetworkRule(signingIdentifier:)` before we ever see them, so
/// every flow that reaches `handleNewFlow` is a bypass candidate by
/// construction. This utility exists only for the self-bypass guard
/// — a belt-and-suspenders check that keeps our own extension /
/// tunnel traffic out of the bypass path in case the rule matrix ever
/// accidentally includes it (user-error, misconfigured import, etc.).
enum FlowDecisionEngine {

    /// Anything signed by our own team + bundle prefix must bypass
    /// back to the OS default route so the extension never loops its
    /// own upstream traffic through itself.
    ///
    /// Covers:
    /// - `com.remrearas.Phantom-WG-MacOS`              (main app)
    /// - `com.remrearas.Phantom-WG-MacOS.PhantomTunnel` (tunnel ext.)
    /// - `com.remrearas.Phantom-WG-MacOS.PhantomSplitTunnel`
    static let selfSigningPrefix = "9C5SL5H7CM.com.remrearas.Phantom-WG-MacOS"

    /// Returns `true` when the flow originates from one of our own
    /// processes. `handleNewFlow` translates that into `return false`
    /// (decline the flow) so the OS falls back to default routing.
    static func isOwnProcess(signingIdentifier: String?) -> Bool {
        guard let id = signingIdentifier, !id.isEmpty else { return false }
        return id.hasPrefix(selfSigningPrefix)
    }

    /// Two-pass match: first against the exact signing identifier (with
    /// team prefix when applicable), then against the bundle-ID
    /// namespace. The namespace pass is what captures browser helpers —
    /// Brave's main app signs as `TEAM.com.brave.Browser` while its
    /// network service appears as `com.brave.Browser.helper` (or
    /// `*.com.brave.Browser.helper` on some Chromium builds). The user
    /// adds the browser once; both the main process and every child of
    /// `com.brave.Browser.*` route through bypass.
    ///
    /// Lives in Domain (not the extension) so main-app tests can
    /// exercise the matrix without having to run the proxy provider.
    static func matches(signingID: String, against app: AppEntry) -> Bool {
        // Exact signing identifier, plus subordinate-namespace prefix
        // (e.g. entry "TEAM.com.brave.Browser" matches flow
        // "TEAM.com.brave.Browser.helper").
        if signingID == app.signingIdentifier
            || signingID.hasPrefix(app.signingIdentifier + ".") {
            return true
        }

        // Bundle-ID namespace — covers helpers signed with a different
        // team prefix, or no prefix at all. Checks every position the
        // bundle ID could appear at:
        //   head:     "com.brave.Browser"
        //   head.*:   "com.brave.Browser.helper"
        //   *.tail:   "TEAM.com.brave.Browser"
        //   *.mid.*:  "TEAM.com.brave.Browser.helper"
        let bundleID = app.bundleIdentifier
        if signingID == bundleID
            || signingID.hasPrefix(bundleID + ".")
            || signingID.hasSuffix("." + bundleID)
            || signingID.contains("." + bundleID + ".") {
            return true
        }

        return false
    }
}
