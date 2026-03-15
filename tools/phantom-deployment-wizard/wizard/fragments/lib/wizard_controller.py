"""
Fragment-based Wizard Controller
Manages step transitions without full page reruns
"""

import streamlit as st
from typing import Dict, Callable


class WizardController:
    """Fragment-based wizard controller for smooth step transitions"""

    def __init__(self):
        """Initialize with empty container for clean transitions"""
        self.container = st.empty()
        self.step_registry: Dict[int, Callable] = {}

    def register_step(self, step_index: int, fragment_func: Callable):
        """
        Register a step fragment function

        Args:
            step_index: The step number (0-based)
            fragment_func: The @st.fragment decorated function
        """
        self.step_registry[step_index] = fragment_func

    def render_current_step(self):
        """
        Render only the active step fragment
        This prevents flash by using st.empty() container
        """
        current_step = st.session_state.current_step

        if current_step in self.step_registry:
            # Clear previous content and render new fragment
            with self.container.container():
                self.step_registry[current_step]()
        else:
            # Fallback for non-fragment steps (temporary during migration)
            return False

        return True

    def clear_container(self):
        """Clear the container explicitly if needed"""
        self.container.empty()