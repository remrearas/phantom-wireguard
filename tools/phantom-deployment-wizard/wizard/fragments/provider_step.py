"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Provider Step Fragment

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import streamlit as st
from .lib.utils import get_current_server, update_current_server
from .lib.navigation import NavigationManager


@st.fragment
def provider_step_fragment():
    """Provider selection as fragment - direct implementation"""
    # Set current server index
    st.session_state.current_server_index = 0
    server = get_current_server()

    st.markdown("### Select Provider")

    with st.form("provider_form"):
        providers = [
            {"slug": "vultr", "name": "Vultr"},
            {"slug": "digitalocean", "name": "DigitalOcean"}
        ]

        provider_choice = st.radio(
            "Choose a provider:",
            options=range(len(providers)),
            format_func=lambda x: providers[x]['name'],
            key="provider_radio"
        )

        col1, col2 = st.columns(2)
        with col1:
            back = st.form_submit_button("← Back", use_container_width=True)
        with col2:
            submitted = st.form_submit_button("Next →", use_container_width=True)

        if back:
            NavigationManager.back(2)  # Go to SSH step
            st.rerun()

        if submitted:
            # Save selected provider
            update_current_server('provider', providers[provider_choice])
            server['deployment_config']['provider'] = providers[provider_choice]
            NavigationManager.next(4)  # Go to Region step
            st.rerun()