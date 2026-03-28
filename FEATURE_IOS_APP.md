# Phantom-WG iOS Client Application (Beta)

> Ghost Mode on iOS — WireGuard over WebSocket

The Phantom-WG iOS client brings Ghost Mode to your pocket. It connects to your
Phantom-WG server through a WebSocket tunnel (wstunnel) and transfers your WireGuard
traffic as standard HTTPS.

**Join the TestFlight beta:**

[![TestFlight](https://img.shields.io/badge/TestFlight-Join_Beta-blue?style=for-the-badge&logo=apple)](https://testflight.apple.com/join/5Kt55AXd)

---

## How It Works

### Server Setup

The server administrator exports the client configuration using `phantom-casper-ios`.
This command generates a JSON output containing WireGuard interface settings, peer
information, and wstunnel parameters — ready to be scanned or transferred to the iOS app.

![Server-side end-user workflow](assets/feature-ios-app/recordings/end-user-workflow-opt.gif)

### Client Connection

On the iOS side, the app reads the configuration and establishes the connection:
wstunnel opens a WebSocket tunnel to the server, and WireGuard routes traffic
through it — all handled transparently within the app.

![iOS client connection](assets/feature-ios-app/ios_recording.gif)

---

## License

Copyright (c) 2025 Riza Emre ARAS <r.emrearas@proton.me>

This software is licensed under the AGPL-3.0 license. See [LICENSE](LICENSE) for details.

For third-party licenses, see [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES).

---

<!--suppress HtmlDeprecatedAttribute -->

<div align="center">

![Phantom Logo](documentation/docs/assets/static/images/phantom-horizontal-master-midnight-phantom.svg)

</div>