import Foundation

// MARK: - Split Tunneling Configuration

/// App-wide split tunneling configuration. Shared between the main app
/// and the PhantomSplitTunnel system extension via App Group UserDefaults —
/// both processes decode this single object from one JSON blob.
///
/// The gate is `isEnabled`: when false the whole feature is inert and
/// the tunnel behaves as if split tunneling didn't exist, yet the user's
/// app list survives for the next activation.
///
/// Semantics are exclude-only: applications in `apps` bypass the active
/// tunnel (routed through the physical interface instead). Every other
/// flow stays on the default OS route, which normally means the tunnel.
struct SplitTunnelingConfiguration: Codable, Equatable {
    var isEnabled: Bool
    var apps: [AppEntry]

    /// Empty, disabled baseline. Used for first-run state and Reset.
    static let `default` = SplitTunnelingConfiguration(
        isEnabled: false,
        apps: []
    )

    enum CodingKeys: String, CodingKey {
        case isEnabled = "is_enabled"
        case apps
    }
}

// MARK: - App Entry

/// A single application selected for split tunneling. Identity is the
/// bundle identifier; the team identifier is captured at pick-time so
/// the system extension can match flows via `sourceAppSigningIdentifier`
/// (format: `<teamID>.<bundleID>`) without re-reading code signatures.
///
/// `lastKnownPath` is refreshed by the reconcile pass and is only used
/// for icon lookup in the UI; the tunnel side never depends on it.
struct AppEntry: Codable, Equatable, Identifiable {
    var bundleIdentifier: String
    var teamIdentifier: String
    var teamName: String?
    var displayName: String
    var lastKnownPath: String?

    var id: String { bundleIdentifier }

    enum CodingKeys: String, CodingKey {
        case bundleIdentifier = "bundle_identifier"
        case teamIdentifier = "team_identifier"
        case teamName = "team_name"
        case displayName = "display_name"
        case lastKnownPath = "last_known_path"
    }
}
