#!/usr/bin/env python3
"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
WireGuard is a registered trademark of Jason A. Donenfeld.

Generate directory index HTML files for Phantom vendor artifacts.
Creates navigable directory listings with file sizes and SHA-256 hashes.

Usage:
    python generate_directory_indexes.py <directory>
"""

import hashlib
import html
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")


def format_size(size):
    """Format file size in human-readable units."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def compute_sha256(file_path):
    """Compute SHA-256 hex digest for a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def create_index_html(directory_path, root_path=None):
    """Create an index.html file for a directory."""
    directory = Path(directory_path)
    if root_path:
        root = Path(root_path)
        relative_path = directory.relative_to(root)
    else:
        relative_path = Path()

    items = []
    for item in sorted(directory.iterdir()):
        if item.name.startswith(".") or item.name == "index.html":
            continue

        stat = item.stat()

        if item.is_dir():
            items.append(
                {
                    "name": item.name,
                    "is_dir": True,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "size": None,
                    "sha256": None,
                }
            )
        else:
            items.append(
                {
                    "name": item.name,
                    "is_dir": False,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "size": stat.st_size,
                    "sha256": compute_sha256(item),
                }
            )

    # Build breadcrumb
    breadcrumb_parts = []
    if relative_path != Path():
        current = Path()
        breadcrumb_parts.append(("Vendor Artifacts", "../" * len(relative_path.parts)))
        for part in relative_path.parts:
            current = current / part
            depth = len(relative_path.parts) - len(current.parts)
            breadcrumb_parts.append((part, "../" * depth if depth > 0 else "./"))
    else:
        breadcrumb_parts.append(("Vendor Artifacts", "./"))

    dir_count = sum(1 for i in items if i["is_dir"])
    file_count = sum(1 for i in items if not i["is_dir"])
    total_size = sum(i["size"] for i in items if i["size"])
    title_path = str(relative_path) if str(relative_path) != "." else "Home"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phantom Vendor Artifacts - {title_path}</title>
    <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" integrity="sha512-DTOQO9RWCH3ppGqcWaEA1BIZOC6xxalwEsw9c2QQeAIftl+Vegovlnee1c9QX4TctnWMn13TZye+giMm8e2LwA==" crossorigin="anonymous" referrerpolicy="no-referrer" />
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Share Tech Mono', monospace;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e8eaed;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(15, 24, 35, 0.95);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            border: 1px solid rgba(74, 158, 255, 0.2);
        }}
        .header {{
            background: linear-gradient(135deg, #0f1419 0%, #1a2332 100%);
            padding: 30px;
            border-bottom: 2px solid #4a9eff;
        }}
        h1 {{
            font-family: 'Orbitron', monospace;
            font-size: 28px;
            color: #4a9eff;
            margin-bottom: 15px;
            text-shadow: 0 0 10px rgba(74, 158, 255, 0.5);
        }}
        .breadcrumb {{
            font-size: 14px;
            color: #9aa0a6;
        }}
        .breadcrumb a {{
            color: #4a9eff;
            text-decoration: none;
            transition: color 0.3s;
        }}
        .breadcrumb a:hover {{
            color: #74b3ff;
            text-decoration: underline;
        }}
        .breadcrumb span {{
            margin: 0 8px;
            color: #495057;
        }}
        .content {{
            padding: 20px 30px 30px;
        }}
        .stats {{
            background: rgba(26, 35, 50, 0.5);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            border: 1px solid rgba(74, 158, 255, 0.1);
            font-size: 14px;
            color: #9aa0a6;
        }}
        .table-wrapper {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            border-radius: 8px;
            background: rgba(26, 35, 50, 0.2);
            scrollbar-width: thin;
            scrollbar-color: rgba(74, 158, 255, 0.3) rgba(15, 24, 35, 0.5);
        }}
        .table-wrapper::-webkit-scrollbar {{ height: 8px; }}
        .table-wrapper::-webkit-scrollbar-track {{ background: rgba(15, 24, 35, 0.5); border-radius: 4px; }}
        .table-wrapper::-webkit-scrollbar-thumb {{ background: rgba(74, 158, 255, 0.3); border-radius: 4px; }}
        .table-wrapper::-webkit-scrollbar-thumb:hover {{ background: rgba(74, 158, 255, 0.5); }}
        table {{
            width: 100%;
            min-width: 600px;
            border-collapse: collapse;
        }}
        thead {{
            background: rgba(26, 35, 50, 0.3);
            border-bottom: 2px solid rgba(74, 158, 255, 0.2);
        }}
        th {{
            text-align: left;
            padding: 12px;
            font-weight: 600;
            color: #4a9eff;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid rgba(57, 75, 97, 0.3);
            font-size: 14px;
        }}
        tr:hover {{ background: rgba(74, 158, 255, 0.05); }}
        .icon {{ display: inline-block; width: 20px; margin-right: 8px; text-align: center; }}
        .dir-icon {{ color: #fbbc04; }}
        .file-icon {{ color: #34a853; }}
        a {{ color: #e8eaed; text-decoration: none; transition: color 0.3s; }}
        a:hover {{ color: #4a9eff; }}
        .size {{ color: #9aa0a6; font-size: 13px; }}
        .date {{ color: #9aa0a6; font-size: 13px; }}
        .hash {{
            font-size: 11px;
            color: #7c8a96;
            font-family: 'Share Tech Mono', monospace;
            word-break: break-all;
            max-width: 280px;
            cursor: pointer;
            position: relative;
        }}
        .hash:hover {{ color: #4a9eff; }}
        .hash .copy-btn {{
            display: inline-block;
            margin-left: 6px;
            font-size: 10px;
            color: #4a9eff;
            opacity: 0;
            transition: opacity 0.2s;
        }}
        .hash:hover .copy-btn {{ opacity: 1; }}
        .toast {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #4a9eff;
            color: #0f1419;
            padding: 10px 20px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
            z-index: 100;
        }}
        .toast.show {{ opacity: 1; }}
        .empty {{
            text-align: center;
            padding: 40px;
            color: #9aa0a6;
            font-style: italic;
        }}
        .footer {{
            background: linear-gradient(135deg, #0f1419 0%, #1a2332 100%);
            padding: 20px 30px;
            border-top: 2px solid rgba(74, 158, 255, 0.2);
            margin-top: 30px;
        }}
        .footer-content {{ text-align: center; font-size: 13px; color: #9aa0a6; }}
        .footer-content p {{ margin: 5px 0; }}
        .footer-content a {{ color: #4a9eff; text-decoration: none; }}
        .footer-content a:hover {{ color: #74b3ff; text-decoration: underline; }}
        .footer-tech {{ font-size: 11px; color: #6c757d; margin-top: 8px; }}

        @media (max-width: 768px) {{
            .container {{ border-radius: 0; margin: 0; }}
            body {{ padding: 0; }}
            .header {{ padding: 20px; }}
            h1 {{ font-size: 22px; }}
            .content {{ padding: 15px; }}
            .hash-col {{ display: none; }}
            .size-col {{ display: none; }}
        }}
        @media (max-width: 480px) {{
            h1 {{ font-size: 18px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-cube"></i> Phantom Vendor Artifacts</h1>
            <div class="breadcrumb">
                {' <span>/</span> '.join(
                    f'<a href="{path}">{html.escape(name)}</a>'
                    for name, path in breadcrumb_parts
                )}
            </div>
        </div>

        <div class="content">
            <div class="stats">
                <i class="fas fa-folder"></i> {dir_count} directories,
                <i class="fas fa-file"></i> {file_count} files,
                <i class="fas fa-database"></i> {format_size(total_size)}
            </div>

            {generate_table(items) if items else '<div class="empty">No files or directories found</div>'}
        </div>

        <div class="footer">
            <div class="footer-content">
                <p>Copyright (c) 2025 R&#x131;za Emre ARAS</p>
                <p class="footer-tech">WireGuard&reg; is a registered trademark of Jason A. Donenfeld</p>
            </div>
        </div>
    </div>

    <div class="toast" id="toast">SHA-256 copied</div>

    <script>
    function copyHash(hash) {{
        navigator.clipboard.writeText(hash).then(function() {{
            var t = document.getElementById('toast');
            t.classList.add('show');
            setTimeout(function() {{ t.classList.remove('show'); }}, 1500);
        }});
    }}
    </script>
</body>
</html>"""

    return html_content


def generate_table(items):
    """Generate the file listing table with SHA-256 column."""
    rows = []
    sorted_items = sorted(items, key=lambda x: (not x["is_dir"], x["name"].lower()))

    for item in sorted_items:
        if item["is_dir"]:
            link = f"{item['name']}/index.html"
            icon = '<i class="fas fa-folder icon dir-icon"></i>'
            name_display = f'<a href="{link}">{html.escape(item["name"])}/</a>'
        else:
            link = item["name"]
            icon = '<i class="fas fa-file-alt icon file-icon"></i>'
            name_display = f'<a href="{link}">{html.escape(item["name"])}</a>'

        size_cell = (
            f'<td class="size size-col">{format_size(item["size"])}</td>'
            if item["size"]
            else '<td class="size size-col">-</td>'
        )

        if item["sha256"]:
            sha = item["sha256"]
            hash_cell = (
                f'<td class="hash hash-col" onclick="copyHash(\'{sha}\')" '
                f'title="Click to copy full hash">'
                f"{sha}"
                f'<span class="copy-btn"><i class="fas fa-copy"></i></span>'
                f"</td>"
            )
        else:
            hash_cell = '<td class="hash hash-col">-</td>'

        date_cell = (
            f'<td class="date">'
            f'{item["modified"].strftime("%Y-%m-%d %H:%M")}'
            f"</td>"
        )

        rows.append(f"""
            <tr>
                <td>{icon}{name_display}</td>
                {size_cell}
                {hash_cell}
                {date_cell}
            </tr>""")

    return f"""
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th class="size-col">Size</th>
                        <th class="hash-col">SHA-256</th>
                        <th>Modified</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
    """


def process_directory_tree(root_dir):
    """Process entire directory tree and create index files."""
    root = Path(root_dir)

    if not root.exists():
        logging.error("Directory %s does not exist", root)
        return False

    processed = 0

    for dirpath, dirnames, _filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        current_dir = Path(dirpath)
        html_content = create_index_html(current_dir, root)
        index_path = current_dir / "index.html"

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logging.info("Created: %s", index_path.relative_to(root.parent))
        processed += 1

    logging.info("Created %d index files", processed)
    return True


def main():
    """Entry point."""
    if len(sys.argv) < 2:
        logging.error("Usage: python generate_directory_indexes.py <directory>")
        sys.exit(1)

    target_dir = sys.argv[1]
    logging.info("Generating directory indexes for: %s", target_dir)

    if not process_directory_tree(target_dir):
        sys.exit(1)


if __name__ == "__main__":
    main()
