import Testing
import Foundation
@testable import Phantom_WG_Mac

// MARK: - AppEntry

@Suite("SplitTunnelingConfiguration — AppEntry Codable round-trip")
struct AppEntryCodableTests {

    @Test("Developer-ID entry round-trips verbatim")
    func developerIDRoundTrip() throws {
        let entry = AppEntry(
            signingIdentifier: "KL8N8XSYF4.com.brave.Browser",
            bundleIdentifier: "com.brave.Browser",
            displayName: "Brave Browser",
            teamName: "Brave Software, Inc.",
            lastKnownPath: "/Applications/Brave Browser.app"
        )

        let data = try JSONEncoder().encode(entry)
        let decoded = try JSONDecoder().decode(AppEntry.self, from: data)
        #expect(decoded == entry)
    }

    @Test("Apple platform-signed entry round-trips (no team prefix)")
    func applePlatformRoundTrip() throws {
        let entry = AppEntry(
            signingIdentifier: "com.apple.Safari",
            bundleIdentifier: "com.apple.Safari",
            displayName: "Safari",
            teamName: nil,
            lastKnownPath: "/Applications/Safari.app"
        )
        let data = try JSONEncoder().encode(entry)
        let decoded = try JSONDecoder().decode(AppEntry.self, from: data)
        #expect(decoded == entry)
    }
}

// MARK: - InterfaceSelection

@Suite("SplitTunnelingConfiguration — InterfaceSelection Codable")
struct InterfaceSelectionCodableTests {

    @Test("Auto encodes as \"auto\" string")
    func autoEncoded() throws {
        let encoded = try JSONEncoder().encode(InterfaceSelection.auto)
        let json = String(data: encoded, encoding: .utf8)
        #expect(json == "\"auto\"")
    }

    @Test("Auto round-trips")
    func autoRoundTrip() throws {
        let data = try JSONEncoder().encode(InterfaceSelection.auto)
        let decoded = try JSONDecoder().decode(InterfaceSelection.self, from: data)
        #expect(decoded == .auto)
    }

    @Test("Explicit encodes as \"explicit:<name>\" string")
    func explicitEncoded() throws {
        let encoded = try JSONEncoder().encode(InterfaceSelection.explicit(name: "en0"))
        let json = String(data: encoded, encoding: .utf8)
        #expect(json == "\"explicit:en0\"")
    }

    @Test("Explicit round-trips")
    func explicitRoundTrip() throws {
        let data = try JSONEncoder().encode(InterfaceSelection.explicit(name: "en0"))
        let decoded = try JSONDecoder().decode(InterfaceSelection.self, from: data)
        #expect(decoded == .explicit(name: "en0"))
    }
}

// MARK: - SplitTunnelingConfiguration

@Suite("SplitTunnelingConfiguration — full Codable round-trip")
struct SplitTunnelingConfigurationCodableTests {

    @Test("Default configuration round-trips")
    func defaultRoundTrip() throws {
        let config = SplitTunnelingConfiguration.default
        let data = try JSONEncoder().encode(config)
        let decoded = try JSONDecoder().decode(SplitTunnelingConfiguration.self, from: data)
        #expect(decoded == config)
    }

    @Test("Full configuration with apps and explicit interface round-trips")
    func fullConfigRoundTrip() throws {
        let config = SplitTunnelingConfiguration(
            isEnabled: true,
            interfaceSelection: .explicit(name: "en0"),
            apps: [
                AppEntry(
                    signingIdentifier: "com.apple.Safari",
                    bundleIdentifier: "com.apple.Safari",
                    displayName: "Safari",
                    teamName: nil,
                    lastKnownPath: "/Applications/Safari.app"
                ),
                AppEntry(
                    signingIdentifier: "KL8N8XSYF4.com.brave.Browser",
                    bundleIdentifier: "com.brave.Browser",
                    displayName: "Brave Browser",
                    teamName: "Brave Software, Inc.",
                    lastKnownPath: "/Applications/Brave Browser.app"
                )
            ]
        )
        let data = try JSONEncoder().encode(config)
        let decoded = try JSONDecoder().decode(SplitTunnelingConfiguration.self, from: data)
        #expect(decoded == config)
        #expect(decoded.apps.count == 2)
        #expect(decoded.interfaceSelection == .explicit(name: "en0"))
    }
}