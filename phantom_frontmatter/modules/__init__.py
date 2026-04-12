"""
Phantom-WG Frontmatter — Module Plugins

Each module under this package provides a specific functionality:
    - setup/  Bootstrap (init) and factory reset (clean) for the host
    - ghost/  Runtime lifecycle (start/stop/restart/status) and client
              config snippet emission for the wstunnel + socat egress
              data path

All modules inherit from BaseModule and are discovered dynamically by
the FrontmatterAPI core at runtime.
"""

from .base import BaseModule

__all__ = ["BaseModule"]
