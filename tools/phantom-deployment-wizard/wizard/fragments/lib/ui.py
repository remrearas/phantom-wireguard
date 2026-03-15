"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

UI helper functions

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import streamlit as st
import requests
import base64
import json
import os
from pathlib import Path
from .api import fetch_api


def custom_spinner(text):
    """Display custom Phantom-branded spinner"""
    st.markdown(f"""
        <div style="text-align: center; padding: 20px;">
            <div class="phantom-spinner"></div>
            <p style="color: #00d4ff; margin-top: 10px;">{text}</p>
        </div>
    """, unsafe_allow_html=True)


def inject_custom_style():
    """Remove all Streamlit deploy button and add smooth transitions"""
    st.markdown("""
        <style>
            /* Hide Streamlit deploy button */
            .stAppDeployButton {display: none;}

            /* Smooth fade-in for main content */
            .main .block-container {
                animation: fadeIn 0.3s ease-in;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            /* Smooth spinner appearance */
            .stSpinner > div {
                animation: fadeIn 0.2s ease-in;
            }
        </style>
    """, unsafe_allow_html=True)


def show_tor_status():
    """Display Tor connection status and IP address"""
    try:
        response = requests.get("https://check.torproject.org/api/ip", timeout=5)
        response.raise_for_status()
        data = response.json()

        is_tor = data.get('IsTor', False)
        ip = data.get('IP', 'Unknown')

        if is_tor:
            st.success(f":shield: **Tor Status**: Connected via Tor | **IP**: {ip}")
        else:
            st.warning(f":warning: **Tor Status**: Not using Tor | **IP**: {ip}")

    except Exception as e:
        st.error(f":x: Failed to check Tor status: {e}")


def build_tree_html(tree_data, current_index, prefix=""):
    """
    Recursively build tree HTML from data structure

    Args:
        tree_data: List of tree nodes (dict with type, label, index, children)
        current_index: Current step index for status indicators
        prefix: Current line prefix for nested items

    Returns:
        HTML string for the tree
    """
    html_lines = []

    def status(idx):
        if current_index > idx:
            return '<span style="color: #00ff00;">✓</span>'
        elif current_index == idx:
            return '<span style="color: #00d4ff;">●</span>'
        else:
            return '<span style="color: #666;">○</span>'

    for i, node in enumerate(tree_data):
        is_last = i == len(tree_data) - 1

        if node["type"] == "group":
            # Group node (has children)
            connector = "└─" if is_last else "├─"
            html_lines.append(f"{prefix}{connector} {node['label']}<br>")

            # Prepare prefix for children
            child_prefix = prefix + ("&nbsp;&nbsp;" if is_last else "│&nbsp;&nbsp;")

            # Recursively build children
            for j, child in enumerate(node["children"]):
                child_is_last = j == len(node["children"]) - 1
                child_connector = "└─" if child_is_last else "├─"

                if child["type"] == "step":
                    html_lines.append(
                        f"{child_prefix}{child_connector} {status(child['index'])} {child['label']}<br>"
                    )
                elif child["type"] == "group":
                    # Nested group
                    child_html = build_tree_html([child], current_index, child_prefix)
                    html_lines.append(child_html)

        elif node["type"] == "step":
            # Step node (leaf)
            connector = "└─" if is_last else "├─"
            html_lines.append(f"{prefix}{connector} {status(node['index'])} {node['label']}<br>")

    return "".join(html_lines)


def show_progress_sidebar(current_step):
    """Display corporate file-tree style sidebar with flexible data-driven structure"""

    config_path = Path(__file__).parent.parent.parent / "configurations" / "sidebar.json"
    with open(config_path, 'r') as f:
        sidebar_configuration = json.load(f)

    # Step name to index mapping
    step_index = sidebar_configuration.get("step_index", {})
    tree_structure = sidebar_configuration.get("tree_structure", {})

    current_index = step_index.get(current_step, 0)

    # Check if TOR_MODE is enabled
    is_tor_mode = bool(os.environ.get('TOR_MODE') == '1')
    is_prod_mode = bool(os.environ.get('PROD_MODE') == '1')

    with st.sidebar:
        # Logo at top - centered, no lightbox
        # Current file: wizard/fragments/lib/ui.py
        # Target: assets/phantom-logo.svg (project root)
        logo_path = Path(__file__).parent.parent.parent / "assets" / "phantom-logo.svg"
        with open(logo_path, "rb") as f:
            logo_data = base64.b64encode(f.read()).decode()

        st.markdown(f"""
            <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                <img src="data:image/svg+xml;base64,{logo_data}" width="280" style="pointer-events: none; max-width: 100%;">
            </div>
        """, unsafe_allow_html=True)

        # Only show Tor Status Section if TOR_MODE is enabled
        if is_tor_mode:
            # Tor Status Section - styled like Token Status
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("**TOR STATUS**")
            with col2:
                if st.button("↻", key="refresh_tor_sidebar", help="Refresh Tor status"):
                    if 'tor_data_cache' in st.session_state:
                        del st.session_state.tor_data_cache
                    st.rerun()

            # Fetch and cache Tor status
            if 'tor_data_cache' not in st.session_state:
                try:
                    response = requests.get("https://check.torproject.org/api/ip", timeout=5)
                    response.raise_for_status()
                    data = response.json()
                    st.session_state.tor_data_cache = data
                except (requests.RequestException, requests.Timeout, ValueError):
                    st.session_state.tor_data_cache = {'IsTor': False, 'IP': 'Unable to check'}

            # Display Tor status in sidebar style
            tor_data = st.session_state.tor_data_cache
            is_tor = tor_data.get('IsTor', False)
            ip = tor_data.get('IP', 'Unknown')

            if is_tor:
                status_text = "Connected"
                status_color = "#00d4ff"
            else:
                status_text = "Not connected"
                status_color = "#ff6b6b"

            # Build IP line conditionally (hide IP in production mode)
            if is_prod_mode:
                ip_line = ""
            else:
                ip_line = f"<br>IP&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ip}"

            st.markdown(f"""
                <div style='font-family: monospace; font-size: 12px; line-height: 1.6; color: #e0e0e0; margin-left: 8px; margin-top: -10px;'>
                    Status&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color: {status_color};'>{status_text}</span>{ip_line}
                </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

        # Progress tree
        st.markdown("**DEPLOYMENT PROGRESS**")

        # Build tree HTML from structure
        tree_html = build_tree_html(tree_structure, current_index)

        st.markdown(f"""
            <div style='font-family: monospace; font-size: 13px; line-height: 1.8; color: #e0e0e0;'>
                {tree_html}
            </div>
        """, unsafe_allow_html=True)

        # Token Status (if set) - NOW AT BOTTOM
        if st.session_state.get('token'):
            # Only fetch token info if not cached or refresh requested
            if 'token_info' not in st.session_state or st.session_state.get('refresh_token_requested', False):
                token_info = fetch_api(f"/token/{st.session_state.token}/info")

                if token_info and isinstance(token_info, dict):
                    st.session_state.token_info = token_info
                    st.session_state.refresh_token_requested = False  # Reset refresh flag

            # Display cached token info
            if 'token_info' in st.session_state:
                token_info = st.session_state.token_info

                st.markdown("<br>", unsafe_allow_html=True)

                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("**TOKEN STATUS**")
                with col2:
                    if st.button("↻", key="refresh_token_sidebar", help="Refresh token status"):
                        st.session_state.refresh_token_requested = True
                        st.rerun()

                st.markdown(f"""
                    <div style='font-family: monospace; font-size: 12px; line-height: 1.6; color: #e0e0e0; margin-left: 8px; margin-top: -10px;'>
                        Balance&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{token_info.get('balance_usd', '$0.00')}<br>
                        Servers&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{token_info.get('servers', 0)}<br>
                        Days Left&nbsp;&nbsp;&nbsp;{token_info.get('days_remaining', 0)}<br>
                        Burn Rate&nbsp;&nbsp;&nbsp;{token_info.get('burn_rate_usd', '$0.00')}
                    </div>
                """, unsafe_allow_html=True)

        # Copyright - Always at bottom
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
            <div style='font-family: monospace; font-size: 10px; line-height: 1.6; color: #666;'>
                © 2025 Rıza Emre ARAS<br>
                All Rights Reserved<br>
                <br>
                WireGuard® is a registered<br>
                trademark of Jason A. Donenfeld.<br>
                <br>
                <a href="https://sporestack.com/" target="_blank" style="color: #888; text-decoration: none;">SporeStack</a> VPS (also GPU and<br>
                baremetal!) hosting for Monero,<br>
                Bitcoin, and Bitcoin Cash
            </div>
        """, unsafe_allow_html=True)
