"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Phantom Documentation Kit Library
"""

from .main import (
    load_config,
    Colors,
    run_command,
    check_mkdocs,
    check_node,
    check_docker_environment,
    check_docker_package,
    VendorManager,
    print_banner,
    setup_mkdocs_logging
)

# Always try to import DockerManager if docker package is available
# This allows remote Docker connections even without local Docker
try:
    from .docker import DockerManager
except ImportError:
    # Docker module not available (missing dependencies)
    DockerManager = None

from .logging import (
    get_logger,
    init_logging,
    log_info
)

# Build __all__ dynamically based on what's available
__all__ = [
    'load_config',
    'Colors',
    'run_command',
    'check_mkdocs',
    'check_node',
    'check_docker_environment',
    'check_docker_package',
    'VendorManager',
    'print_banner',
    'setup_mkdocs_logging',
    'get_logger',
    'init_logging',
    'log_info'
]

# Only add DockerManager to __all__ if it's available
if DockerManager is not None:
    __all__.append('DockerManager')