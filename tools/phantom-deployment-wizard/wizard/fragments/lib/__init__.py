"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Phantom Deployment Wizard - Library Module

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

from .utils import get_current_server, update_current_server, generate_ssh_keypair
from .api import fetch_api, post_api
from .ui import (
    custom_spinner,
    inject_custom_style,
    show_tor_status,
    build_tree_html,
    show_progress_sidebar
)
from .wizard_controller import WizardController
from .state_manager import WizardState
from .navigation import NavigationManager

__all__ = [
    # Utils
    'get_current_server',
    'update_current_server',
    'generate_ssh_keypair',
    # API
    'fetch_api',
    'post_api',
    # UI
    'custom_spinner',
    'inject_custom_style',
    'show_tor_status',
    'build_tree_html',
    'show_progress_sidebar',
    # Controllers
    'WizardController',
    'WizardState',
    'NavigationManager',
]
