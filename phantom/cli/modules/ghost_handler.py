"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Ghost Module UI Handler

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
from .base import BaseUIHandler

# Rich imports
try:
    from rich.table import Table
    from rich import box

    RICH_AVAILABLE = True
except ImportError:
    Table = None
    box = None
    RICH_AVAILABLE = False


class GhostUIHandler(BaseUIHandler):
    """ UI Handler for Ghost module """

    def get_module_name(self):
        """ Get module name """
        return "ghost"

    def handle_enable(self):
        """Handle enable action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold magenta]👻 Enable Ghost Mode[/bold magenta] - [dim]Mask WireGuard traffic as HTTPS[/dim]",
                box=box.DOUBLE,
                border_style="magenta"
            ))
        else:
            self.print("👻 Enable Ghost Mode", style="bold magenta")
            self.print("=" * 40)

        self.print("\nGhost Mode masks WireGuard traffic as HTTPS using wstunnel.")
        self.print("This helps bypass restrictive firewalls and censorship.")
        self.print("\n⚠️  Domain Required: You must have a domain with an A record pointing to this server.")

        # Get domain
        domain = self.prompt("\nEnter your domain (e.g., vpn.example.com)")
        if not domain:
            self.print_error("Domain is required for Ghost Mode")
            return None

        # Show summary
        if self.console and RICH_AVAILABLE and Table:
            # noinspection PyUnboundLocalVariable
            summary_table = Table(
                show_header=False,
                box=box.SIMPLE,
                title="🚀 Ghost Mode Configuration Summary"
            )

            summary_table.add_column("Task", style="bold cyan", width=30)
            summary_table.add_column("Details", width=50)

            summary_table.add_row("SSL Certificate", f"Let's Encrypt for {domain}")
            summary_table.add_row("WebSocket Tunnel", "wstunnel on port 443")
            summary_table.add_row("Protocol", "WSS (WebSocket Secure)")
            summary_table.add_row("Firewall Rules", "Port 51820 restricted to localhost")
            summary_table.add_row("Service", "systemd service for auto-start")

            self.console.print("\n")
            self.console.print(summary_table)
        else:
            self.print(f"\nGhost Mode will be enabled with SSL on {domain}:443")
            self.print("\nConfiguration summary:")
            self.print("  • SSL Certificate: Let's Encrypt")
            self.print("  • WebSocket Tunnel: Port 443")
            self.print("  • Firewall: Port 51820 restricted")

        if self.confirm("\nProceed with Ghost Mode activation?"):
            return {"domain": domain}
        return None

    def handle_disable(self):
        """Handle disable action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold red]🚫 Disable Ghost Mode[/bold red] - [dim]Restore normal WireGuard operation[/dim]",
                box=box.DOUBLE,
                border_style="red"
            ))
        else:
            self.print("🚫 Disable Ghost Mode", style="bold red")
            self.print("=" * 40)

        self.print("\nThis will disable Ghost Mode and restore normal WireGuard operation.")

        if self.confirm("\nAre you sure you want to disable Ghost Mode?"):
            return {}
        return None

    def handle_status(self):
        """Handle status action"""
        self.clear_screen()

        # Get status
        response = self.api.execute("ghost", "status")

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]👻 Ghost Mode Status[/bold cyan] - [dim]Current censorship-resistant connection status[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("👻 Ghost Mode Status", style="bold cyan")
            self.print("=" * 40)

        # Display status if enabled
        if response.success and response.data.get("enabled"):
            self._display_status_table(response.data)
        elif response.success:
            self.print("\n⚪ Ghost Mode is currently disabled", style="yellow")
            self.print("\nTo enable Ghost Mode, use the 'Enable Ghost Mode' option from the menu.")

        return {}

    def _display_status_table(self, data):
        """Display Ghost Mode status in a table format"""
        if self.console and RICH_AVAILABLE and Table:
            # Connection details
            details_table = Table(
                show_header=True,
                header_style="bold cyan",
                box=box.ROUNDED,
                title="🔐 Connection Details"
            )

            details_table.add_column("Property", style="bold", width=20)
            details_table.add_column("Value", style="white", width=50)

            # Add status
            status = data.get('status', 'Unknown')
            if status.lower() == 'active':
                status_display = f"[green]● {status}[/green]"
            else:
                status_display = f"[yellow]● {status}[/yellow]"

            details_table.add_row("Status", status_display)
            details_table.add_row("Domain", data.get('domain', 'N/A'))
            details_table.add_row("Server IP", data.get('server_ip', 'N/A'))
            details_table.add_row("Protocol", f"{data.get('protocol', 'wss').upper()} (Port {data.get('port', 443)})")
            details_table.add_row("Secret", data.get('secret', 'N/A'))
            details_table.add_row("Activated", data.get('activated_at', 'Unknown'))

            self.console.print("\n")
            self.console.print(details_table)

            # Services status
            services = data.get('services', {})
            if services:
                services_table = Table(
                    show_header=True,
                    header_style="bold yellow",
                    box=box.ROUNDED,
                    title="🔧 Service Status"
                )

                services_table.add_column("Service", style="bold", width=20)
                services_table.add_column("Status", justify="center", width=15)
                services_table.add_column("Description", width=40)

                for service_name, status in services.items():
                    if status == "active":
                        status_icon = "[green]● Active[/green]"
                        desc = "Running and accepting connections"
                    else:
                        status_icon = "[red]○ Inactive[/red]"
                        desc = "Service is not running"

                    services_table.add_row(
                        service_name,
                        status_icon,
                        desc
                    )

                self.console.print("\n")
                self.console.print(services_table)

            # Command
            if data.get('connection_command'):
                self.console.print(f"\n[bold blue]📋 Connection Command:[/bold blue]")
                self.console.print(f"   [cyan]{data['connection_command']}[/cyan]")

            # Export info
            if data.get('client_export_info'):
                self.console.print(f"\n[bold green]💡 Client Configuration Export:[/bold green]")
                self.console.print(f"   [yellow]{data['client_export_info']}[/yellow]")
        else:
            # Fallback
            self.print("\n🔐 Connection Details:")
            self.print(f"  Status: {data.get('status', 'Unknown')}")
            self.print(f"  Domain: {data.get('domain', 'N/A')}")
            self.print(f"  Server IP: {data.get('server_ip', 'N/A')}")
            self.print(f"  Protocol: {data.get('protocol', 'wss').upper()} (Port {data.get('port', 443)})")
            self.print(f"  Secret: {data.get('secret', 'N/A')}")
            self.print(f"  Activated: {data.get('activated_at', 'Unknown')}")

            services = data.get('services', {})
            if services:
                self.print("\n🔧 Service Status:")
                for service, status in services.items():
                    self.print(f"  {service}: {status}")

            if data.get('connection_command'):
                self.print(f"\n📋 Connection Command:")
                self.print(f"  {data['connection_command']}")

    # noinspection PyMethodMayBeStatic
    def _format_bytes(self, bytes_val):
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} PB"
