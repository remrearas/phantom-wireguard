"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: Multihop Modülü Durum Yöneticisi
    =================================

    VPN bağlantı durumunu takip eder, konfigürasyon durumunu kaydeder,
    istatistikleri günceller ve sistem durumunu yönetir.

EN: Multihop Module State Manager
    ==============================

    Tracks VPN connection state, records configuration state,
    updates statistics and manages system state.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from .common_tools import (
    VPN_INTERFACE_NAME
)


class StateManager:

    def __init__(self, config: Dict[str, Any], logger, save_config_func):
        self.config = config
        self.logger = logger
        self._save_config = save_config_func

        # State variables
        self.multihop_enabled = False
        self.active_exit = None

    def load_multihop_state(self):
        multihop_config = self.config.get("multihop", {})
        self.multihop_enabled = multihop_config.get("enabled", False)
        self.active_exit = multihop_config.get("active_exit")

        if self.multihop_enabled and self.active_exit:
            self.logger.info(f"Multihop enabled: {self.active_exit}")

    def save_multihop_state(self):
        self.config["multihop"] = {
            "enabled": self.multihop_enabled,
            "active_exit": self.active_exit,
            "vpn_interface_name": VPN_INTERFACE_NAME,
            "updated_at": datetime.now().isoformat()
        }
        self._save_config()

    def update_state(self, enabled: bool, active_exit: Optional[str] = None):
        self.multihop_enabled = enabled
        self.active_exit = active_exit if enabled else None
        self.save_multihop_state()
