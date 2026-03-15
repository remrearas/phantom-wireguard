# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS
# Licensed under AGPL-3.0 - see LICENSE file for details
# Third-party licenses - see THIRD_PARTY_LICENSES file for details
# WireGuard® is a registered trademark of Jason A. Donenfeld.

import json
import pytest
import shutil


@pytest.fixture
def test_environment(tmp_path):
    config_dir = tmp_path / 'config'
    config_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "dns": {
            "primary": "1.1.1.1",
            "secondary": "1.0.0.1"
        }
    }

    config_path = config_dir / 'phantom.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    test_data = {
        'tmp_path': tmp_path,
        'config_path': config_path
    }

    yield test_data

    shutil.rmtree(tmp_path)
