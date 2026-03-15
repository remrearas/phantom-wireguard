"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Check Server Step Fragment

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import streamlit as st
import time
import socket
from .lib.api import fetch_api
from .lib.navigation import NavigationManager


@st.fragment
def check_server_step_fragment():
    """Check server availability as fragment - auto-check implementation"""
    st.markdown("### :satellite: Check Server Available")

    # Get machine_id from deployment config
    phantom_server = st.session_state.servers[0]
    machine_id = phantom_server.get('deployment_config', {}).get('machine_id')

    if not machine_id:
        st.error("No machine_id found. Please go back and deploy the server first.")
        if st.button(":leftwards_arrow_with_hook: Back to Deployment", use_container_width=True, key="check_server_back_btn"):
            NavigationManager.back(9)
            st.rerun()
    else:
        # Initialize check states
        if 'ip_check_complete' not in st.session_state:
            st.session_state.ip_check_complete = False
        if 'ssh_check_complete' not in st.session_state:
            st.session_state.ssh_check_complete = False
        if 'server_ipv4' not in st.session_state:
            st.session_state.server_ipv4 = None
        if 'server_info' not in st.session_state:
            st.session_state.server_info = None

        # Initialize retry counters
        if 'ip_poll_count' not in st.session_state:
            st.session_state.ip_poll_count = 0
        if 'ssh_poll_count' not in st.session_state:
            st.session_state.ssh_poll_count = 0

        # Phase 1: Check for IP address
        st.markdown("#### :one: Phase 1: Waiting for IP Address")

        ip_status_placeholder = st.empty()
        max_attempts = 60  # 5 minutes (60 * 5 seconds)

        if not st.session_state.ip_check_complete:
            if st.session_state.ip_poll_count < max_attempts:
                with ip_status_placeholder.container():
                    st.info(f"🔍 Polling for IP address... (Attempt {st.session_state.ip_poll_count + 1}/{max_attempts})")
                    # Fetch server info
                    server_info = fetch_api(f"/token/{st.session_state.token}/servers/{machine_id}")

                if server_info and 'ipv4' in server_info and server_info['ipv4']:
                    st.session_state.server_ipv4 = server_info['ipv4']
                    st.session_state.server_info = server_info
                    st.session_state.ip_check_complete = True
                    st.session_state.ip_poll_count = 0  # Reset counter
                    # Save IPv4 to deployment config
                    phantom_server['deployment_config']['ipv4'] = server_info['ipv4']

                    with ip_status_placeholder.container():
                        st.success(f":white_check_mark: IP Address: `{server_info['ipv4']}`")
                    time.sleep(1)  # Brief pause before continuing
                    st.rerun()
                else:
                    st.session_state.ip_poll_count += 1
                    time.sleep(5)
                    st.rerun()
            else:
                with ip_status_placeholder.container():
                    st.error("❌ Timeout: IP address not assigned after 5 minutes")
                    if st.button("🔄 Retry", key="ip_retry_btn"):
                        st.session_state.ip_poll_count = 0
                        st.rerun()
        else:
            st.success(f":white_check_mark: IP Address: `{st.session_state.server_ipv4}`")
            with st.expander("📋 View Server Information"):
                st.json(st.session_state.server_info)

        # Phase 2: Check SSH connection (auto-starts when IP is ready)
        if st.session_state.ip_check_complete:
            st.markdown("#### :two: Phase 2: Waiting for SSH Connection")

            ssh_status_placeholder = st.empty()
            max_ssh_attempts = 30  # 5 minutes (30 * 10 seconds)

            if not st.session_state.ssh_check_complete:
                if st.session_state.ssh_poll_count < max_ssh_attempts:
                    with ssh_status_placeholder.container():
                        st.info(f"🔌 Testing SSH connectivity to {st.session_state.server_ipv4}:22... (Attempt {st.session_state.ssh_poll_count + 1}/{max_ssh_attempts})")

                    try:
                        # Try to connect to SSH port (22)
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(3)
                        result = sock.connect_ex((st.session_state.server_ipv4, 22))
                        sock.close()

                        if result == 0:
                            st.session_state.ssh_check_complete = True
                            st.session_state.ssh_poll_count = 0  # Reset counter

                            with ssh_status_placeholder.container():
                                st.success(":white_check_mark: SSH Connection is active!")

                            time.sleep(1)  # Brief pause before auto-advancing
                            st.rerun()
                        else:
                            st.session_state.ssh_poll_count += 1
                            time.sleep(10)
                            st.rerun()
                    except (socket.error, OSError, socket.timeout):
                        st.session_state.ssh_poll_count += 1
                        time.sleep(10)
                        st.rerun()
                else:
                    with ssh_status_placeholder.container():
                        st.error("❌ Timeout: SSH connection not available after 5 minutes")
                        if st.button("🔄 Retry SSH", key="ssh_retry_btn"):
                            st.session_state.ssh_poll_count = 0
                            st.rerun()
            else:
                st.success(":white_check_mark: SSH Connection is active!")

        # Auto-advance when both checks complete
        if st.session_state.ip_check_complete and st.session_state.ssh_check_complete:
            st.markdown("---")
            st.success(":tada: Server is available and ready!")

            # Auto-advance placeholder
            advance_placeholder = st.empty()
            with advance_placeholder.container():
                st.info("🚀 Auto-advancing to installation in 2 seconds...")

            time.sleep(2)
            # Clear check states for future use
            st.session_state.ip_check_complete = False
            st.session_state.ssh_check_complete = False
            st.session_state.ip_poll_count = 0
            st.session_state.ssh_poll_count = 0

            NavigationManager.next(11)
            st.rerun()