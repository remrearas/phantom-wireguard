import Foundation

// MARK: - Split Tunneling Configuration

/// App-wide split tunneling configuration. Persisted as JSON
/// (`split-tunneling.json`) in the shared App Group container by the
/// main app's `SplitTunnelingStore`. File-based persistence sidesteps
/// `cfprefsd` cross-process caching issues that UserDefaults would
/// otherwise expose when a sandboxed extension reads values written
/// by the main app under a different security context.
///
/// Delivery to the extension does **not** go through the file: the
/// main app packs this blob into `providerConfiguration["split_config"]`
/// at save-time (initial boot path) and sends it via opcode `0x00`
/// messages for live reloads afterwards. The extension decodes the
/// JSON handed to it and never touches the App Group file directly.
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
    var interfaceSelection: InterfaceSelection
    var apps: [AppEntry]

    /// Empty, disabled baseline. Used for first-run state and Reset.
    static let `default` = SplitTunnelingConfiguration(
        isEnabled: false,
        interfaceSelection: .auto,
        apps: []
    )

    enum CodingKeys: String, CodingKey {
        case isEnabled = "is_enabled"
        case interfaceSelection = "interface_selection"
        case apps
    }

    /// Forward-compatible decoder — missing `interface_selection` (old
    /// Phase-2-in-progress blobs) defaults to `.auto`.
    init(isEnabled: Bool, interfaceSelection: InterfaceSelection, apps: [AppEntry]) {
        self.isEnabled = isEnabled
        self.interfaceSelection = interfaceSelection
        self.apps = apps
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.isEnabled = try container.decode(Bool.self, forKey: .isEnabled)
        self.apps = try container.decode([AppEntry].self, forKey: .apps)
        self.interfaceSelection = try container.decodeIfPresent(
            InterfaceSelection.self,
            forKey: .interfaceSelection
        ) ?? .auto
    }
}

// MARK: - Interface Selection

/// Which physical interface bypass relays should bind to. `auto` lets
/// the extension's `NWPathMonitor` pick the primary non-tunnel path;
/// `explicit` pins to a specific BSD name (`en0`, `en1`, …) the user
/// chose from the picker.
///
/// Stored verbatim as `"auto"` or `"explicit:en0"` so the serialized
/// form reads at a glance and migrations stay trivial.
enum InterfaceSelection: Codable, Equatable, Hashable {
    case auto
    case explicit(name: String)

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let raw = try container.decode(String.self)
        if raw == "auto" {
            self = .auto
        } else if raw.hasPrefix("explicit:") {
            self = .explicit(name: String(raw.dropFirst("explicit:".count)))
        } else {
            self = .auto
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .auto:
            try container.encode("auto")
        case .explicit(let name):
            try container.encode("explicit:\(name)")
        }
    }
}

// MARK: - App Entry

/// A single application selected for split tunneling. Identity is the
/// **code signing identifier** exactly as reported by the Security
/// framework — for Developer ID apps this is `<teamID>.<bundleID>`,
/// for Apple platform-signed apps it's just `<bundleID>` (e.g.
/// `com.apple.Safari`). At runtime the extension matches this string
/// against each flow's `sourceAppSigningIdentifier` via
/// `FlowDecisionEngine.matches` — the OS performs no filtering based
/// on this value. The match matrix covers both exact signing IDs and
/// bundle-ID namespace prefixes, so a single entry for a Chromium-based
/// browser (`TEAM.com.vendor.Browser`) also captures its helper
/// processes (`com.vendor.Browser.helper`) without user intervention.
///
/// `bundleIdentifier`, `displayName`, `teamName` and `lastKnownPath`
/// are UI metadata — no runtime logic depends on them.
struct AppEntry: Codable, Equatable, Identifiable {
    var signingIdentifier: String
    var bundleIdentifier: String
    var displayName: String
    var teamName: String?
    var lastKnownPath: String?

    var id: String { signingIdentifier }

    enum CodingKeys: String, CodingKey {
        case signingIdentifier = "signing_identifier"
        case bundleIdentifier = "bundle_identifier"
        case displayName = "display_name"
        case teamName = "team_name"
        case lastKnownPath = "last_known_path"
        // Legacy — still decoded so Phase-2-in-progress configs migrate.
        case teamIdentifier = "team_identifier"
    }

    init(
        signingIdentifier: String,
        bundleIdentifier: String,
        displayName: String,
        teamName: String? = nil,
        lastKnownPath: String? = nil
    ) {
        self.signingIdentifier = signingIdentifier
        self.bundleIdentifier = bundleIdentifier
        self.displayName = displayName
        self.teamName = teamName
        self.lastKnownPath = lastKnownPath
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.bundleIdentifier = try container.decode(String.self, forKey: .bundleIdentifier)
        self.displayName = try container.decode(String.self, forKey: .displayName)
        self.teamName = try container.decodeIfPresent(String.self, forKey: .teamName)
        self.lastKnownPath = try container.decodeIfPresent(String.self, forKey: .lastKnownPath)

        if let value = try container.decodeIfPresent(String.self, forKey: .signingIdentifier) {
            self.signingIdentifier = value
        } else if let team = try container.decodeIfPresent(String.self, forKey: .teamIdentifier),
                  !team.isEmpty {
            // Forward-migrate old `team_identifier + bundle_identifier` blobs.
            self.signingIdentifier = "\(team).\(bundleIdentifier)"
        } else {
            throw DecodingError.keyNotFound(
                CodingKeys.signingIdentifier,
                DecodingError.Context(
                    codingPath: container.codingPath,
                    debugDescription: "AppEntry missing signing identifier"
                )
            )
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(signingIdentifier, forKey: .signingIdentifier)
        try container.encode(bundleIdentifier, forKey: .bundleIdentifier)
        try container.encode(displayName, forKey: .displayName)
        try container.encodeIfPresent(teamName, forKey: .teamName)
        try container.encodeIfPresent(lastKnownPath, forKey: .lastKnownPath)
    }
}
