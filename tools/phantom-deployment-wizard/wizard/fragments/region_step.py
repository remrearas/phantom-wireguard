"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Region Step Fragment

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import streamlit as st
import time
from .lib.api import fetch_api
from .lib.utils import get_current_server, update_current_server
from .lib.ui import custom_spinner
from .lib.navigation import NavigationManager


@st.fragment
def region_step_fragment():
    """Region selection as fragment - direct implementation"""
    # Set current server index
    st.session_state.current_server_index = 0
    server = get_current_server()

    st.markdown("### Select Region")

    provider = server['provider']

    # Check if regions are cached
    if server['regions_cache'] is None:
        placeholder = st.empty()
        with placeholder.container():
            custom_spinner(f"Loading regions for {provider['name']}...")

        time.sleep(0.5)
        regions = fetch_api(f"/slugs/regions?provider={provider['slug']}")

        if regions:
            update_current_server('regions_cache', regions[:15])

        placeholder.empty()

    regions = server['regions_cache']

    if regions and isinstance(regions, list) and len(regions) > 0:
        with st.form("region_form"):
            def format_region(x):
                r = regions[x]
                if isinstance(r, dict):
                    return f"{r.get('name', r.get('slug', 'Unknown'))} ({r.get('slug', '-')})"
                return str(r)

            region_choice = st.selectbox(
                "Choose a region:",
                options=range(len(regions)),
                format_func=format_region,
                key="region_select"
            )

            col1, col2 = st.columns(2)
            with col1:
                back = st.form_submit_button("← Back", use_container_width=True)
            with col2:
                submitted = st.form_submit_button("Next →", use_container_width=True)

            if back:
                # Clear cache and go back to provider step
                update_current_server('regions_cache', None)
                update_current_server('region', None)
                NavigationManager.back(3)  # Go to provider step
                st.rerun()

            if submitted:
                # Save selected region
                update_current_server('region', regions[region_choice])
                server['deployment_config']['region'] = regions[region_choice]
                NavigationManager.next(5)  # Go to OS step
                st.rerun()
    else:
        st.error("Failed to load regions. Please try again.")

        if st.button("← Back", use_container_width=True):
            update_current_server('regions_cache', None)
            update_current_server('region', None)
            NavigationManager.back(3)
            st.rerun()