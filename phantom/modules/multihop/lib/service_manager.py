"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: Multihop Modülü Servis Yöneticisi
    ==================================

    Sistemd servislerini yönetir, monitor daemon'u kontrol eder,
    servis durumlarını izler ve otomatik yeniden başlatma sağlar.

EN: Multihop Module Service Manager
    ================================

    Manages systemd services, controls monitor daemon,
    tracks service status and provides automatic restart capabilities.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import re
import time
from pathlib import Path
from typing import Dict, Any

from phantom.api.exceptions import MultihopError
from .common_tools import MONITOR_SERVICE_NAME, SERVICE_START_DELAY


class ServiceManager:

    def __init__(self, config: Dict[str, Any], logger, run_command_func):
        self.config = config
        self.logger = logger
        self._run_command = run_command_func

    def start_monitor_service(self):
        try:
            service_file = Path(f"/etc/systemd/system/{MONITOR_SERVICE_NAME}.service")
            if not service_file.exists():
                raise MultihopError(
                    f"Monitor service not installed. Please run installation script "
                    f"to create {MONITOR_SERVICE_NAME}.service"
                )

            # Stop if already running
            self._run_command(["systemctl", "stop", MONITOR_SERVICE_NAME])

            # Start service
            result = self._run_command(["systemctl", "start", MONITOR_SERVICE_NAME])

            if not result["success"]:
                stderr = result.get('stderr', 'Unknown error')
                raise MultihopError(f"Failed to start monitor service: {stderr}")

            # Verify service is running
            time.sleep(SERVICE_START_DELAY)
            check_result = self._run_command(["systemctl", "is-active", MONITOR_SERVICE_NAME])

            if check_result["stdout"].strip() != "active":
                raise MultihopError("Monitor service started but is not active")

            self.logger.info("Monitor service started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start monitor service: {e}")
            raise MultihopError(
                f"Monitor service required but failed to start: {str(e)}\n"
                f"Multihop functionality requires systemd monitor service."
            )

    def stop_monitor_service(self):
        try:
            check_result = self._run_command(["systemctl", "is-active", MONITOR_SERVICE_NAME])
            if check_result["stdout"].strip() == "active":
                self._run_command(["systemctl", "stop", MONITOR_SERVICE_NAME])
                self.logger.info("Monitor service stopped")

        except Exception as e:
            self.logger.error(f"Failed to stop monitor service: {e}")

    def get_monitor_status(self) -> Dict[str, Any]:
        try:
            # Check systemd service
            result = self._run_command(["systemctl", "is-active", MONITOR_SERVICE_NAME])
            if result["stdout"].strip() == "active":
                # Get PID from service
                pid_result = self._run_command(["systemctl", "show", "-p", "MainPID", MONITOR_SERVICE_NAME])
                pid = None
                if pid_result["success"]:
                    pid_match = re.search(r'MainPID=(\d+)', pid_result["stdout"])
                    if pid_match:
                        pid = pid_match.group(1)

                return {
                    "monitoring": True,
                    "type": "systemd",
                    "pid": pid
                }

            # No active monitoring
            return {
                "monitoring": False,
                "type": None,
                "pid": None
            }

        except (OSError, ValueError) as e:
            self.logger.warning(f"Failed to get monitor service status: {e}")
            return {
                "monitoring": False,
                "type": None,
                "pid": None
            }