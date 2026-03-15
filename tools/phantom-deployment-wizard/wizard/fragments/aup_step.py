"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

AUP Step Fragment

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import streamlit as st
from .lib.api import fetch_api
from .lib.navigation import NavigationManager
from .lib.state_manager import WizardState


@st.fragment
def aup_step_fragment():
    """AUP acceptance as fragment - smooth transitions!"""
    st.markdown("### :scroll: Acceptable Use Policy")

    # Cache AUP text in session state to avoid repeated API calls
    if not WizardState.get('aup_text_cache'):
        aup_text = fetch_api("/aup", return_text=True)
        WizardState.set('aup_text_cache', aup_text)
    else:
        aup_text = WizardState.get('aup_text_cache')

    if aup_text:
        # Display AUP in scrollable text area
        st.text_area(
            "SporeStack Acceptable Use Policy",
            value=aup_text if isinstance(aup_text, str) else str(aup_text),
            height=300,
            disabled=True,
            key="aup_fragment_text"
        )

        st.markdown("---")

        # AUP acceptance checkbox
        accepted = st.checkbox(
            "I have read and accept the Acceptable Use Policy",
            key="aup_fragment_checkbox"
        )

        # Navigation buttons
        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                ":leftwards_arrow_with_hook: Back",
                use_container_width=True,
                key="aup_back_btn"
            ):
                # Clear token when going back to token step
                WizardState.set('token', None)
                WizardState.set('token_info', None)
                WizardState.set('aup_accepted', False)

                # Reset deployment configs for all servers
                servers = WizardState.get('servers', [])
                for server in servers:
                    server['deployment_config'] = {}

                # Navigate back - fragments need explicit rerun
                NavigationManager.back(0)
                st.rerun()

        with col2:
            if st.button(
                "Next :arrow_right:",
                use_container_width=True,
                type="primary",
                disabled=not accepted,
                key="aup_next_btn"
            ):
                # Save acceptance state
                WizardState.set('aup_accepted', True)

                # Navigate forward - fragments need explicit rerun
                NavigationManager.next(2)
                st.rerun()
    else:
        # Error loading AUP
        st.error("Failed to load Acceptable Use Policy.")

        if st.button(
            ":leftwards_arrow_with_hook: Back",
            use_container_width=True,
            key="aup_error_back_btn"
        ):
            # Reset state and go back
            WizardState.set('token', None)
            WizardState.set('token_info', None)
            WizardState.set('aup_accepted', False)

            NavigationManager.back(0)
            st.rerun()