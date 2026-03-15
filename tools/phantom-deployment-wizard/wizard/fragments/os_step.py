"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

OS Step Fragment

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import streamlit as st
import time
from .lib.api import fetch_api
from .lib.utils import get_current_server, update_current_server
from .lib.ui import custom_spinner
from .lib.navigation import NavigationManager


@st.fragment
def os_step_fragment():
    """OS selection as fragment - auto-advancing implementation"""
    # Set current server index
    st.session_state.current_server_index = 0
    server = get_current_server()
    provider = server['provider']
    region = server['region']

    st.markdown("### Select Operating System")

    # Check if OS list is cached
    if server['os_cache'] is None:
        placeholder = st.empty()
        with placeholder.container():
            custom_spinner(f"Loading OS options for {region['name']}...")

        time.sleep(0.5)
        os_list = fetch_api(f"/slugs/os?provider={provider['slug']}")

        if os_list:
            update_current_server('os_cache', os_list)

        placeholder.empty()

    os_list = server['os_cache']

    if os_list and isinstance(os_list, list) and len(os_list) > 0:
        # Try to find debian-13, fallback to debian-12
        selected_os = None
        for os_option in os_list:
            if os_option.get('slug') == 'debian-13':
                selected_os = os_option
                break

        # Fallback to debian-12 if debian-13 not found
        if not selected_os:
            for os_option in os_list:
                if os_option.get('slug') == 'debian-12':
                    selected_os = os_option
                    break

        if selected_os:
            # Save selected OS
            update_current_server('os', selected_os)
            server['deployment_config']['os'] = selected_os

            if isinstance(selected_os, dict):
                os_display = selected_os.get('name', selected_os.get('slug', 'Unknown'))
            else:
                os_display = str(selected_os)

            st.success(f":white_check_mark: Selected: {os_display}")
            time.sleep(1)

            # Auto-advance to flavor step
            NavigationManager.next(6)
            st.rerun()
        else:
            st.error("Neither Debian 13 nor Debian 12 is available for this provider.")

            if st.button("← Back", use_container_width=True):
                update_current_server('os_cache', None)
                update_current_server('os', None)
                NavigationManager.back(4)  # Go back to Region step
                st.rerun()
    else:
        st.error("Failed to load operating systems. Please try again.")

        if st.button("← Back", use_container_width=True):
            update_current_server('os_cache', None)
            NavigationManager.back(4)  # Go back to Region step
            st.rerun()