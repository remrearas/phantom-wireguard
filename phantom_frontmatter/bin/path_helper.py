"""
Phantom-WG Frontmatter — Path Helper

Ensures the phantom_frontmatter package can be imported from bin/
scripts regardless of invocation method.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0
"""

import sys
from pathlib import Path


def setup_path() -> None:
    """Add the phantom_frontmatter project root to sys.path.

    Resolves the package root by walking up from this file until a
    directory containing ``phantom_frontmatter/__init__.py`` is found.

    After calling setup_path(), ``import phantom_frontmatter`` works
    regardless of where the script was invoked from.
    """
    this_file = Path(__file__).resolve()
    # .../phantom_frontmatter/bin/path_helper.py
    #   → parent = .../phantom_frontmatter/bin/
    #   → parent.parent = .../phantom_frontmatter/
    #   → parent.parent.parent = project root
    project_root = this_file.parent.parent.parent

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
