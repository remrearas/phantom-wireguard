"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Flavor/Size Step Fragment

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import streamlit as st
import time
from .lib.utils import get_current_server, update_current_server
from .lib.api import fetch_api
from .lib.ui import custom_spinner
from .lib.navigation import NavigationManager


@st.fragment
def flavor_step_fragment():
    """Flavor/size selection as fragment - direct implementation"""
    # Set current server index
    st.session_state.current_server_index = 0
    server = get_current_server()
    provider = server['provider']

    st.markdown("### Select Server Size")

    # Fetch flavors if not cached
    if server['flavors_cache'] is None:
        placeholder = st.empty()
        with placeholder.container():
            custom_spinner("Loading server options...")

        time.sleep(0.5)
        all_flavors = fetch_api(f"/slugs/flavors?provider={provider['slug']}")

        # Filter: VPS only, no GPU, no baremetal
        flavors = [f for f in all_flavors
                  if f.get('type') == 'vps'
                  and 'gpu' not in f.get('features', [])]

        # Sort by price
        flavors = sorted(flavors, key=lambda x: x.get('price', 0))

        # Cache all filtered flavors
        update_current_server('flavors_cache', flavors)
        placeholder.empty()

    flavors = server['flavors_cache']

    if not flavors:
        st.error("Failed to load server sizes.")
        if st.button("← Back", key="flavor_error_back"):
            update_current_server('flavors_cache', None)
            NavigationManager.back(4)  # Go to Region step
            st.rerun()
        return

    # Helper function to format flavor display
    def format_flavor(idx):
        f = flavors[idx]
        cpu = f.get('cores', 0)
        memory_gb = f.get('memory', 0) / 1024  # MB -> GB (float for precision)
        storage = f.get('disk', 0)
        cost = f.get('price', 0) / 100  # cents -> dollars
        return f"{cpu}vCPU / {memory_gb:.1f}GB RAM / {storage}GB Disk - ${cost:.2f}/day"

    # Flavor selection (outside form for live updates)
    flavor_choice = st.selectbox(
        "Choose a server size:",
        options=range(len(flavors)),
        format_func=format_flavor,
        key="flavor_select"
    )

    # Live preview of selected configuration
    st.markdown("#### Selected Configuration")
    selected = flavors[flavor_choice]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("CPU", f"{selected.get('cores', 0)} vCPU")
        ram_gb = selected.get('memory', 0) / 1024
        st.metric("RAM", f"{ram_gb:.1f} GB")
        st.metric("Storage", f"{selected.get('disk', 0)} GB")

    with col2:
        st.metric("Bandwidth", f"{selected.get('bandwidth_per_month', 0)} TB/mo")
        price_dollars = selected.get('price', 0) / 100
        st.metric("Price", f"${price_dollars:.2f}/day")

    # Debug view - JSON representation
    with st.expander(":mag: Selected Configuration (JSON)"):
        st.json(selected)

    st.markdown("---")

    # Navigation buttons (fragment style - no form)
    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "← Back",
            use_container_width=True,
            key="flavor_back_btn"
        ):
            # Clear caches when going back
            update_current_server('flavors_cache', None)
            update_current_server('os_cache', None)  # Clear OS cache to allow auto-advance on next forward
            NavigationManager.back(4)  # Go to Region step (skip auto OS)
            st.rerun()

    with col2:
        if st.button(
            "Next →",
            use_container_width=True,
            type="primary",
            key="flavor_next_btn"
        ):
            # Save selected flavor
            update_current_server('flavor', flavors[flavor_choice])
            server['deployment_config']['flavor'] = flavors[flavor_choice]
            NavigationManager.next(7)  # Go to Quote step
            st.rerun()