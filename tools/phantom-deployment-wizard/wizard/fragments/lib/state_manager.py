"""
Centralized State Management for Wizard
Handles persistent state across fragments
"""

import streamlit as st
from typing import Any


class WizardState:
    """Centralized state management for wizard steps"""

    # Keys that should persist across steps
    PERSISTENT_KEYS = [
        'current_step',
        'token',
        'token_info',
        'aup_accepted',
        'aup_text_cache',
        'ssh_public_key',
        'ssh_private_key',
        'servers',
        'deployment_initiated',
        'deployment_response',
        'ip_check_complete',
        'ssh_check_complete',
        'server_ipv4',
        'server_info',
        'install_initiated',
        'install_output'
    ]

    @classmethod
    def init(cls):
        """Initialize persistent state with default values"""
        # Current step tracking
        if 'current_step' not in st.session_state:
            st.session_state.current_step = 0

        # Initialize servers list
        if 'servers' not in st.session_state:
            st.session_state.servers = [{
                "name": "phantom",
                "type": "phantom",
                "deployment_config": {},
                "provider": None,
                "region": None,
                "os": None,
                "flavor": None,
                "quote": None,
                "days": 1,
                "ssh_private_key": None,
                "ssh_public_key": None,
                "regions_cache": None,
                "os_cache": None,
                "flavors_cache": None
            }]

        # Initialize current server index
        if 'current_server_index' not in st.session_state:
            st.session_state.current_server_index = 0

        # Initialize other persistent keys as None
        for key in cls.PERSISTENT_KEYS:
            if key not in st.session_state and key not in ['current_step', 'servers']:
                st.session_state[key] = None

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        Safely get a value from session state

        Args:
            key: The state key
            default: Default value if key doesn't exist

        Returns:
            The value or default
        """
        return st.session_state.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any):
        """
        Set a value in session state

        Args:
            key: The state key
            value: The value to set
        """
        st.session_state[key] = value

    @classmethod
    def clear_step_data(cls, step_name: str):
        """
        Clear temporary data for a specific step
        Helps with memory optimization

        Args:
            step_name: Name of the step to clear temp data for
        """
        temp_keys = [
            k for k in st.session_state
            if k.startswith(f"{step_name}_temp_")
        ]
        for key in temp_keys:
            del st.session_state[key]

    @classmethod
    def reset_to_start(cls):
        """Reset the wizard to the beginning"""
        # Keep only the servers structure
        servers = st.session_state.get('servers', [])

        # Clear everything
        for key in list(st.session_state.keys()):
            del st.session_state[key]

        # Restore servers and reset step
        st.session_state.servers = servers
        st.session_state.current_step = 0
        cls.init()

    @classmethod
    def get_current_server(cls) -> dict:
        """Get the current server configuration (phantom server)"""
        servers = st.session_state.get('servers', [])
        if servers:
            return servers[0]
        return {}

    @classmethod
    def update_current_server(cls, updates: dict):
        """Update the current server configuration"""
        if 'servers' in st.session_state and st.session_state.servers:
            st.session_state.servers[0].update(updates)