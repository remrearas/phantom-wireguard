"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Configuration Data Models

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
from dataclasses import dataclass
from typing import Dict, Any

from phantom.models.base import BaseModel


@dataclass
class TweakSettingsResponse(BaseModel):
    settings: Dict[str, bool]
    descriptions: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for setting, value in self.settings.items():
            result[setting] = value
        for setting, desc in self.descriptions.items():
            result[f"{setting}_description"] = desc
        return result


@dataclass
class TweakModificationResult(BaseModel):
    setting: str
    new_value: bool
    old_value: bool
    message: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "setting": self.setting,
            "new_value": self.new_value,
            "old_value": self.old_value,
            "message": self.message,
            "description": self.description
        }
