"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Multihop Module UI Handler

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
from .base import BaseUIHandler


class MultihopUIHandler(BaseUIHandler):
    """ UI Handler for Multihop module """

    def get_module_name(self):
        """ Get module name """
        return "multihop"

    def handle_import_vpn_config(self):
        """Handle import_vpn_config action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]📥 Import VPN Configuration[/bold cyan] - [dim]Add external VPN as multihop exit node[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("📥 Import VPN Configuration", style="bold blue")
            self.print("=" * 40)

        self.print("\nImport an external VPN configuration to use as exit node.")
        self.print("Supported formats: OpenVPN (.ovpn), WireGuard (.conf)")

        config_path = self.prompt("\nEnter path to VPN config file")
        if not config_path:
            return None

        custom_name = self.prompt("Enter name for this exit node (optional)")

        kwargs = {"config_path": config_path}
        if custom_name and custom_name.strip():
            kwargs["custom_name"] = custom_name.strip()

        return kwargs

    def handle_list_exits(self):
        """Handle list_exits action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]📋 Available Exit Nodes[/bold cyan] - [dim]View configured multihop exit points[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("📋 Available Exit Nodes", style="bold cyan")
            self.print("=" * 40)
        return {}

    def handle_enable_multihop(self):
        """Handle enable_multihop action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]🔀 Enable Multihop VPN[/bold cyan] - [dim]Route traffic through external VPN exit node[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("🔀 Enable Multihop VPN", style="bold green")
            self.print("=" * 40)

        # Get exits
        response = self.api.execute("multihop", "list_exits")
        if not response.success:
            self.print_error("Failed to get exit nodes")
            return None

        exits = response.data.get("exits", [])
        if not exits:
            self.print("\nNo exit nodes available. Import a VPN config first.", style="yellow")
            return None

        # Show exits
        self.print("\nAvailable exit nodes:")
        for exit_node in exits:
            status = "Active" if exit_node.get("active") else "Inactive"
            self.print(f"  - {exit_node.get('name')} ({exit_node.get('type')}) - {status}")

        exit_name = self.prompt("\nEnter exit node name to activate")
        if not exit_name:
            return None

        # Verify exit
        if not any(e.get("name") == exit_name for e in exits):
            self.print_error(f"Exit node '{exit_name}' not found")
            return None

        if self.confirm(f"\nActivate multihop through '{exit_name}'?"):
            return {"exit_name": exit_name}
        return None

    def handle_disable_multihop(self):
        """Handle disable_multihop action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]🚫 Disable Multihop VPN[/bold cyan] - [dim]Route traffic directly through WireGuard[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("🚫 Disable Multihop VPN", style="bold red")
            self.print("=" * 40)

        self.print("\nThis will disable multihop and route traffic directly through WireGuard.")

        if self.confirm("\nAre you sure you want to disable multihop?"):
            return {}
        return None

    def handle_multihop_status(self):
        """Handle multihop_status action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]📊 Multihop Status[/bold cyan] - [dim]Current multihop routing configuration[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("📊 Multihop Status", style="bold cyan")
            self.print("=" * 40)
        return {}

    def handle_status(self):
        """Handle status action (alias for multihop_status)"""
        return self.handle_multihop_status()

    def handle_remove_vpn_config(self):
        """Handle remove_vpn_config action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]🗑️ Remove VPN Configuration[/bold cyan] - [dim]Delete configured exit node[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("🗑️ Remove VPN Configuration", style="bold red")
            self.print("=" * 40)

        # Get exits
        response = self.api.execute("multihop", "list_exits")
        if not response.success:
            self.print_error("Failed to get exit nodes")
            return None

        exits = response.data.get("exits", [])
        if not exits:
            self.print("\nNo exit nodes to remove.", style="yellow")
            return None

        # Show exits
        self.print("\nAvailable exit nodes:")
        for i, exit_node in enumerate(exits, 1):
            self.print(f"  {i}. {exit_node.get('name')} ({exit_node.get('type')})")

        exit_name = self.prompt("\nEnter exit node name to remove")
        if not exit_name:
            return None

        if self.confirm(f"\nRemove exit node '{exit_name}'?"):
            return {"exit_name": exit_name}
        return None

    def handle_test_vpn(self):
        """Handle test_vpn action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]🧪 Test VPN Connection[/bold cyan] - [dim]Check multihop exit node connectivity[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("🧪 Test VPN Connection", style="bold yellow")
            self.print("=" * 40)

        self.print("\nThis will test connectivity through the active multihop connection.")
        self.print("\nPress Enter to start the test...")
        self.prompt("")

        return {}

    def handle_reset_state(self):
        """Handle reset_state action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]🔄 Reset Multihop State[/bold cyan] - [dim]Clear all multihop configurations[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("🔄 Reset Multihop State", style="bold orange")
            self.print("=" * 40)

        self.print("\n⚠️  This will:")
        self.print("  • Disable any active multihop connections")
        self.print("  • Reset routing tables")
        self.print("  • Clear multihop state")
        self.print("\nClients will connect directly through WireGuard.")

        if self.confirm("\nAre you sure you want to reset multihop state?"):
            return {}
        return None

    def handle_get_session_log(self):
        """Handle get_session_log action with live updates"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]📄 Multihop Session Log[/bold cyan] - [dim]Live monitoring of multihop activity[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("📄 Multihop Session Log", style="bold cyan")
            self.print("=" * 40)

        lines = self.prompt("\nNumber of log lines to display", default="50")
        try:
            lines = int(lines)
        except ValueError:
            lines = 50

        # Live mode flag
        return {"lines": lines, "_special": "live_log"}
