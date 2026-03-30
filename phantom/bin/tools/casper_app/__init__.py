"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: Phantom-WG Casper App - Ghost Mode .conf Configuration Exporter
    =========================================================================

    Casper App, Ghost Mode aktifken kullanıcıların Phantom-WG mobil/masaüstü
    uygulamaları için WireGuard .conf formatında konfigürasyon üretir.

    Ana Özellikler:
        - ghost-state.json dosyasından Ghost Mode durumunu kontrol eder
        - Phantom API üzerinden client verilerini alır (Core/export_client)
        - Ghost API'den wstunnel komutunu alır ve parse eder (Ghost/status)
        - AllowedIPs'i sunucu IP'sini hariç tutacak şekilde hesaplar
        - WireGuard .conf formatında [Wstunnel] bölümüyle birlikte çıktı üretir

    Kullanım:
        phantom-casper-app [kullanıcı_adı]

    Çıktı Formatı:
        Ghost Mode aktifken: [Wstunnel] + [Interface] + [Peer]
        Ghost Mode olmadan: [Interface] + [Peer]

EN: Phantom-WG Casper App - Ghost Mode .conf Configuration Exporter
    ====================================================================

    Casper App generates WireGuard .conf format configurations for
    Phantom-WG mobile/desktop applications when Ghost Mode is active.

    Key Features:
        - Checks Ghost Mode status from ghost-state.json file
        - Retrieves client data via Phantom API (Core/export_client)
        - Fetches and parses wstunnel command from Ghost API (Ghost/status)
        - Calculates AllowedIPs to exclude server IP
        - Produces WireGuard .conf output with [Wstunnel] section

    Usage:
        phantom-casper-app [username]

    Output Format:
        With Ghost Mode: [Wstunnel] + [Interface] + [Peer]
        Without Ghost Mode: [Interface] + [Peer]

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from .core import CasperAppService

__all__ = [
    "CasperAppService",
]
