"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ██║   ██║██║╚██╔╝██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Command Executor for Docker tests

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from phantom.models.base import CommandResult


class CommandExecutor:

    def __init__(self, docker_executor):
        self.docker_executor = docker_executor

    def run_command(self, command, **kwargs):
        """
        Docker environment compatible run_command with stdin support.
        Supports all subprocess.run parameters via kwargs.
        """
        # Convert command to string
        if isinstance(command, list):
            if len(command) >= 3 and command[0] == 'sh' and command[1] == '-c':
                cmd_str = f"sh -c '{' '.join(command[2:])}'"
            else:
                cmd_str = ' '.join(command)
        else:
            cmd_str = command

        # Handle stdin data if 'input' parameter provided (like subprocess.run)
        if 'input' in kwargs:
            input_data = kwargs.pop('input')  # Remove from kwargs after extracting
            # Escape single quotes in input data
            escaped_input = str(input_data).replace("'", "'\\''")

            # Check if command uses /dev/stdin (like wg set)
            if isinstance(command, list) and "/dev/stdin" in command:
                # For commands that read from stdin via /dev/stdin
                # Use heredoc for safer multi-line input handling
                cmd_str = f"cat <<'EOF' | {cmd_str}\n{input_data}\nEOF"
            else:
                # Standard pipe for other commands (like wg pubkey)
                cmd_str = f"echo '{escaped_input}' | {cmd_str}"

        # Wrap in shell if command contains shell operators
        if not cmd_str.startswith("sh -c '"):
            if any(char in cmd_str for char in ['>', '<', '|', '&', ';']):
                escaped_command = cmd_str.replace("'", "'\\''")
                cmd_str = f"sh -c '{escaped_command}'"
                print(f"[CMD DEBUG] Shell wrapped: {cmd_str}")

        # Execute command via docker
        result = self.docker_executor.run_command(cmd_str)
        return CommandResult(**result)
