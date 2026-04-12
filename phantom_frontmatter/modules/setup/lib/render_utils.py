"""
Setup Module — Systemd Template Rendering

Pure string substitution against the packaged systemd unit
templates. Takes a template name plus a substitution dict and
returns the rendered text. Placeholders use the ``__NAME__`` form.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0
"""

from pathlib import Path
from typing import Dict


# Templates ship inside phantom_frontmatter/systemd/
TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent / "systemd"


def template_path(template_name: str) -> Path:
    """Return the absolute path to a packaged systemd template."""
    return TEMPLATE_DIR / template_name


def render_template(template_name: str, substitutions: Dict[str, str]) -> str:
    """Read a packaged template and replace ``__KEY__`` placeholders.

    Raises ``FileNotFoundError`` if the template does not exist.
    """
    path = template_path(template_name)
    if not path.exists():
        raise FileNotFoundError(f"Systemd template not found: {path}")

    text = path.read_text()
    for key, value in substitutions.items():
        text = text.replace(f"__{key}__", value)
    return text


def write_unit_file(
    unit_path: Path,
    rendered_content: str,
    logger,
) -> bool:
    """Write a rendered systemd unit to disk.

    The caller is responsible for choosing ``unit_path`` (typically
    ``/etc/systemd/system/<name>.service``) and for issuing the
    ``systemctl daemon-reload`` afterwards.
    """
    try:
        unit_path.parent.mkdir(parents=True, exist_ok=True)
        unit_path.write_text(rendered_content)
        logger.info(f"Wrote systemd unit: {unit_path}")
        return True
    except OSError as e:
        logger.error(f"Failed to write systemd unit {unit_path}: {e}")
        return False