"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: Multihop Modülü Oturum Günlükleyicisi
    ======================================

    VPN oturum verilerini kaydeder, bağlantı geçmişini tutar,
    istatistikleri toplar ve günlük dosyalarını yönetir.

EN: Multihop Module Session Logger
    ===============================

    Records VPN session data, maintains connection history,
    collects statistics and manages log files.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import re
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from textwrap import dedent

from .common_tools import DEFAULT_LOG_LINES, LOG_LEVELS


class SessionLogger:

    def __init__(self, logs_dir: Path, logger):
        self.logs_dir = logs_dir
        self.logger = logger
        self.session_log_path = None

    def init_session_log(self, exit_name: str):
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            self.session_log_path = self.logs_dir / "multihop-session-current.log"

            if self.session_log_path.exists():
                self.session_log_path.unlink()

            with open(self.session_log_path, 'w') as f:
                f.write(dedent("""
                    ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
                    ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
                    ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
                    ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
                    ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
                    ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

                    MULTIHOP HANDSHAKE MONITOR - LIVE SESSION
                    ==========================================
                    """).strip() + "\n")
                f.write(f"Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Exit Server: {exit_name}\n")
                f.write(f"Monitor: Managed by phantom-multihop-monitor.service\n\n")
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] SESSION STARTED - Handshake monitoring active\n")

        except Exception as e:
            self.logger.error(f"Failed to initialize session log: {e}")

    def cleanup_session_log(self):
        try:
            if self.session_log_path and self.session_log_path.exists():
                self.session_log_path.unlink()
                self.session_log_path = None
        except Exception as e:
            self.logger.error(f"Failed to cleanup session log: {e}")

    def get_session_log(self, lines: int = DEFAULT_LOG_LINES, multihop_enabled: bool = False,
                        active_exit: str = None, get_monitor_status_func=None) -> Dict[str, Any]:
        if not multihop_enabled:
            return {
                "active_session": False,
                "message": "No active multihop session"
            }

        session_log_path = self.logs_dir / "multihop-session-current.log"

        if not session_log_path.exists():
            return {
                "active_session": True,
                "log_exists": False,
                "message": "Session log not found"
            }

        try:
            with open(session_log_path, 'r') as f:
                all_lines = f.readlines()

            # Get last N lines
            display_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            # Parse lines for structured data
            parsed_lines = self._parse_log_lines(display_lines)

            # Get monitor status if function provided
            monitor_status = get_monitor_status_func() if get_monitor_status_func else None

            return {
                "active_session": True,
                "log_exists": True,
                "active_exit": active_exit,
                "monitor_status": monitor_status,
                "log_lines": parsed_lines,
                "total_lines": len(all_lines),
                "displayed_lines": len(parsed_lines)
            }

        except Exception as e:
            self.logger.error(f"Failed to read session log: {e}")
            return {
                "active_session": True,
                "log_exists": False,
                "error": str(e)
            }

    def _parse_log_lines(self, lines: List[str]) -> List[Dict[str, Any]]:
        parsed_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Extract timestamp and message
            match = re.match(r'\[(\d{2}:\d{2}:\d{2})] (.+)', line)
            if match:
                timestamp, message = match.groups()

                # Determine log level
                level = self._determine_log_level(message)

                parsed_lines.append({
                    "timestamp": timestamp,
                    "message": message,
                    "level": level
                })
            else:
                # Non-timestamped line (like ASCII art)
                parsed_lines.append({
                    "timestamp": None,
                    "message": line,
                    "level": "INFO"
                })

        return parsed_lines

    # noinspection PyMethodMayBeStatic
    def _determine_log_level(self, message: str) -> str:
        message_upper = message.upper()

        # Check for specific keywords
        for keyword, level in LOG_LEVELS.items():
            if f"[{keyword}]" in message_upper or keyword in message_upper:
                return level

        # Default to INFO
        return "INFO"
