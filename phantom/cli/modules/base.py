"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Base Class for Module UI Handlers

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
from abc import ABC, abstractmethod

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Prompt = None
    Confirm = None
    Table = None


class BaseUIHandler(ABC):
    def __init__(self, api, console=None):
        """Initialize base handler"""
        self.api = api
        self.console = console
        self.module_name = self.get_module_name()

    @abstractmethod
    def get_module_name(self):
        """Get the module name this handler manages"""
        pass

    def handle_action(self, action):
        """ Route action to appropriate handler method"""
        handler_method = getattr(self, f"handle_{action}", None)
        if handler_method:
            return handler_method()
        else:
            # Fallback to generic handler
            return self.handle_generic_action(action)

    # noinspection PyMethodMayBeStatic
    def handle_generic_action(self, _action):
        """Generic handler for actions without specific implementation"""
        return {}

    def print(self, message, style=None):
        """Print with optional styling"""
        if self.console and style:
            self.console.print(message, style=style)
        else:
            print(message)

    def print_error(self, message: str):
        """Print error message"""
        self.print(f"❌ Error: {message}", style="red")

    def print_success(self, message: str):
        """Print success message"""
        self.print(f"✅ {message}", style="green")

    def print_warning(self, message: str):
        """Print warning message"""
        self.print(f"⚠️  {message}", style="yellow")

    # noinspection PyMethodMayBeStatic
    def prompt(self, message, default=None):
        """Get user input"""
        if RICH_AVAILABLE:
            return Prompt.ask(message, default=default)
        else:
            prompt = f"{message}"
            if default:
                prompt += f" [{default}]"
            prompt += ": "
            result = input(prompt)
            return result or default

    # noinspection PyMethodMayBeStatic
    def confirm(self, message, default=False):
        """Get user confirmation"""
        if RICH_AVAILABLE:
            return Confirm.ask(message, default=default)
        else:
            result = input(f"{message} [y/N]: ").lower()
            return result in ["y", "yes"]

    def clear_screen(self):
        """Clear the terminal screen"""
        if self.console:
            self.console.clear()
        else:
            import os
            os.system('clear' if os.name == 'posix' else 'cls')

    # noinspection PyMethodMayBeStatic
    def create_table(self, title=None):
        """Create a new Rich table"""
        if not RICH_AVAILABLE:
            return None

        return Table(
            title=title,
            show_header=True,
            header_style="bold"
        )
