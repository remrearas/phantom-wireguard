<!--
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
Copyright (c) 2025 Riza Emre ARAS <r.emrearas@proton.me>
-->

# Privacy Notice — Spin & Deploy (Provider Wheel)

**Last Updated:** February 2026

## Overview

Spin & Deploy is an open-source, client-side provider selection tool that is part of the Phantom-WG project. It helps you randomly choose privacy-focused VPS providers for your server and exit node configurations. This notice explains how the tool works, what data it handles, and what the listed providers represent.

## About the Listed Providers

The providers listed in this tool were identified through search engine research and AI-assisted analysis. The selection criteria were:

- **Cryptocurrency payment support** — Each provider accepts one or more cryptocurrencies (BTC, XMR, ETH, LTC) as payment methods
- **Privacy-focused approach** — Providers that are known for respecting user privacy in their hosting services
- **Established presence** — Each provider has an official domain, a recognized user base, and a track record in the hosting community

These providers are presented as options for hosting your Phantom-WG configurations. Phantom-WG is here as a tool to ensure full compatibility with your setup. If you cannot decide which provider to go with, this tool can help you make that choice.

## Third-Party Disclaimer

**Phantom-WG has no affiliation, partnership, sponsorship, or business relationship with any of the listed providers.** The providers appear in this tool solely based on the criteria described above. Their inclusion does not constitute an endorsement, recommendation, or guarantee of their services.

Each provider operates independently and is governed by their own terms of service, privacy policies, and acceptable use policies. You are responsible for reviewing and agreeing to a provider's terms before purchasing any service.

## No Affiliate Links

This tool contains **no affiliate links, referral codes, or tracking parameters**. All provider URLs link directly to their official websites. Phantom-WG receives no financial benefit, commission, or compensation of any kind from your choice of provider or any subsequent purchase.

## What Data Does This Tool Collect?

### None.

This tool collects, transmits, and stores **absolutely no data**. Specifically:

| Aspect                     | Detail                                                                                     |
|----------------------------|--------------------------------------------------------------------------------------------|
| **Analytics**              | None — no tracking scripts, pixels, or telemetry                                           |
| **Cookies**                | None — no cookies are set or read                                                          |
| **Network requests**       | One `fetch` call to load `providers.json` from the same origin — no external API calls     |
| **User input**             | The tool accepts no user input beyond button clicks                                        |
| **Storage**                | No localStorage, sessionStorage, IndexedDB, or any other browser storage mechanism is used |
| **Server-side processing** | None — the tool is a static HTML/CSS/JS page with no backend                               |

### How the Wheel Works

1. Provider data is loaded from a local `providers.json` file (same-origin, no external requests)
2. The wheel spin uses `Math.random()` in your browser — the selection is entirely client-side
3. No selection results are recorded, transmitted, or stored anywhere
4. Closing the page discards all state completely

## External Connections

**This tool makes no external connections whatsoever.** All assets — including fonts, stylesheets, scripts, and provider data — are bundled within the project and loaded locally. No external CDNs, APIs, or third-party services are contacted by the application code.

## Hosting & Infrastructure

When accessed via [phantom.tc](https://www.phantom.tc), this tool is served through **Cloudflare Pages**. As a result, standard web infrastructure applies:

- Cloudflare may process standard HTTP metadata (IP address, User-Agent, request headers) as part of serving the page
- This is inherent to any website served through a CDN and is not specific to this tool
- Phantom-WG does not configure, access, or control any Cloudflare analytics, logging, or tracking features
- No additional telemetry, cookies, or tracking scripts are added by Phantom-WG

For details on how Cloudflare handles data, see the [Cloudflare Privacy Policy](https://www.cloudflare.com/privacypolicy/).

If you prefer to avoid any CDN-level processing, you can run this tool locally by cloning the repository and opening the HTML files directly in your browser.

## Open Source and Transparency

This tool is part of the Phantom-WG open-source project. The complete source code — including the provider list, selection logic, and this privacy notice — is publicly available and auditable on GitHub.

The provider list is maintained in a plain `providers.json` file that anyone can inspect. The selection algorithm uses standard browser randomization with no weighting, biasing, or predetermined outcomes.

## Changes to This Notice

This privacy notice may be updated as the tool evolves. Changes will be reflected in this file with an updated date.

## Contact

For questions about this privacy notice or the Spin & Deploy tool:

**Riza Emre ARAS** — [r.emrearas@proton.me](mailto:r.emrearas@proton.me)
