"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Quote Step Fragment

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import streamlit as st
import time
from .lib.utils import get_current_server, update_current_server
from .lib.api import fetch_api
from .lib.ui import custom_spinner
from .lib.navigation import NavigationManager


@st.fragment
def quote_step_fragment():
    """Server quote as fragment - direct implementation"""
    # Set current server index
    st.session_state.current_server_index = 0
    server = get_current_server()
    provider = server['provider']
    flavor = server['flavor']

    st.markdown("### Server Quote")

    st.info(":bulb: Enter the number of days you want to rent the server. This will determine your payment amount in the next step.")

    # Days input (outside form for live updates)
    days = st.number_input(
        "Enter number of days (required):",
        min_value=1,
        max_value=365,
        value=server['days'] if server['days'] else 1,
        step=1,
        key="quote_days_input",
        help="Minimum 1 day, maximum 365 days"
    )

    # Fetch quote if days changed or quote not available
    if server['quote'] is None or server['days'] != days:
        update_current_server('days', days)

        placeholder = st.empty()
        with placeholder.container():
            custom_spinner(f"Fetching quote for {days} day{'s' if days > 1 else ''}...")

        time.sleep(0.5)
        provider_slug = provider.get('slug') if isinstance(provider, dict) else str(provider)
        flavor_slug = flavor.get('slug') if isinstance(flavor, dict) else str(flavor)

        quote_response = fetch_api("/server/quote", params={
            "provider": provider_slug,
            "flavor": flavor_slug,
            "days": days
        })

        if quote_response:
            update_current_server('quote', quote_response)
            server['deployment_config']['quote'] = quote_response
            server['deployment_config']['days'] = days

        placeholder.empty()

    quote = server['quote']

    # Display quote details
    if quote and isinstance(quote, dict):
        st.markdown("#### Quote Details")
        st.json(quote)

        st.markdown("---")

    # Navigation buttons (fragment style - no form)
    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "← Back",
            use_container_width=True,
            key="quote_back_btn"
        ):
            # Clear quote data when going back
            update_current_server('quote', None)
            update_current_server('days', None)
            NavigationManager.back(6)  # Go to Flavor step
            st.rerun()

    with col2:
        # Validate before allowing navigation
        can_proceed = days and days >= 1 and quote and isinstance(quote, dict)

        if st.button(
            "Next →",
            use_container_width=True,
            type="primary",
            disabled=not can_proceed,
            key="quote_next_btn"
        ):
            if not days or days < 1:
                st.error("Please enter a valid number of days (minimum 1).")
            elif not quote or not isinstance(quote, dict):
                st.error("Please wait for quote to load or check API response.")
            else:
                NavigationManager.next(8)  # Go to Deployment Preview
                st.rerun()