"""
Navigation Manager for Fragment-based Wizard
Handles step transitions without st.rerun()
"""

import streamlit as st


class NavigationManager:
    """Handle step transitions without full page rerun"""

    @staticmethod
    def next(target_step: int = None):
        """
        Move to next step without st.rerun()
        Fragment will auto-rerun, preventing full page flash

        Args:
            target_step: Optional specific step to jump to
        """
        if target_step is not None:
            st.session_state.current_step = target_step
        else:
            st.session_state.current_step += 1

        # NO st.rerun() here! Fragment handles its own rerun

    @staticmethod
    def back(target_step: int = None):
        """
        Move to previous step without st.rerun()

        Args:
            target_step: Optional specific step to jump to
        """
        if target_step is not None:
            st.session_state.current_step = target_step
        else:
            st.session_state.current_step -= 1

        # NO st.rerun() here! Fragment handles its own rerun

    @staticmethod
    def can_navigate_forward() -> bool:
        """Check if forward navigation is allowed"""
        current = st.session_state.current_step

        # Add validation logic here based on current step
        if current == 0 and not st.session_state.get('token'):
            return False
        if current == 1 and not st.session_state.get('aup_accepted'):
            return False
        if current == 2 and not st.session_state.get('servers', [{}])[0].get('ssh_public_key'):
            return False

        return True

    @staticmethod
    def can_navigate_back() -> bool:
        """Check if back navigation is allowed"""
        # Generally always allowed unless at step 0
        return st.session_state.current_step > 0