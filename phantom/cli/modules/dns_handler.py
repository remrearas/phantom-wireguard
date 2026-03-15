"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

DNS Module UI Handler

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
from .base import BaseUIHandler


class DNSUIHandler(BaseUIHandler):
    """ UI Handler for DNS module """

    def get_module_name(self):
        """ Get module name """
        return "dns"

    def handle_change_dns_servers(self):
        """Handle change_dns_servers action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]🌐 Change DNS Servers[/bold cyan]\n"
                "[dim]Update primary and secondary DNS servers[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("🌐 Change DNS Servers", style="bold blue")
            self.print("=" * 40)

        self.print("\nCommon DNS Servers:")
        self.print("  • Google: 8.8.8.8, 8.8.4.4")
        self.print("  • Cloudflare: 1.1.1.1, 1.0.0.1")
        self.print("  • Quad9: 9.9.9.9, 149.112.112.112")
        self.print("  • OpenDNS: 208.67.222.222, 208.67.220.220")

        primary = self.prompt("\nEnter primary DNS server", default="8.8.8.8")
        if not primary:
            return None

        secondary = self.prompt("Enter secondary DNS server", default="8.8.4.4")
        if not secondary:
            return None

        if self.confirm(f"\nChange DNS servers to {primary} and {secondary}?"):
            return {
                "primary": primary,
                "secondary": secondary
            }
        return None

    def handle_current_dns_servers(self):
        """Handle current_dns_servers action"""
        self.clear_screen()
        self.print("📋 Current DNS Configuration", style="bold cyan")
        self.print("=" * 40)
        return {}

    def handle_status(self):
        """Handle status action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]📊 DNS Status[/bold cyan]\n"
                "[dim]Current DNS configuration and health check[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("📊 DNS Status", style="bold green")
            self.print("=" * 40)

        return {}

    def handle_get_dns_servers(self):
        """Handle get_dns_servers action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]🌐 Current DNS Servers[/bold cyan]\n"
                "[dim]View active DNS configuration[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("🌐 Current DNS Servers", style="bold cyan")
            self.print("=" * 40)
        return {}

    def handle_test_dns_servers(self):
        """Handle test_dns_servers action"""
        self.clear_screen()

        if self.console:
            from rich.panel import Panel
            from rich import box

            # Show header
            self.console.print(Panel(
                "[bold cyan]🔍 Test DNS Servers[/bold cyan]\n"
                "[dim]Check DNS resolution performance[/dim]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            self.print("🔍 Test DNS Servers", style="bold yellow")
            self.print("=" * 40)

        self.print("\nThis will test DNS resolution using current servers.")

        # Get domain
        domain = self.prompt("\nEnter domain to test (optional)", default="google.com")

        if domain and domain.strip():
            return {"domain": domain.strip()}
        else:
            return {}
