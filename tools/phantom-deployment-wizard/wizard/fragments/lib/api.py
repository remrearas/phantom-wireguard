"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

API interaction functions

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import streamlit as st
import streamlit.components.v1 as components
import requests
import json


# API Configuration
API_BASE = "https://api.sporestack.com"


def _log_error_to_console(error_message):
    """Log error to browser console instead of showing in UI"""
    # Sanitize error message for JavaScript
    safe_message = json.dumps(error_message)

    # Inject JavaScript to log error to console
    components.html(
        f"""
        <script>
            console.error('API Error:', {safe_message});
        </script>
        """,
        height=0
    )


def fetch_api(endpoint, params=None, return_text=False):
    """Fetch data from SporeStack API"""
    try:
        response = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=10)
        response.raise_for_status()

        if return_text:
            return response.text
        else:
            return response.json()
    except requests.Timeout:
        _log_error_to_console("Request timed out")
        st.error("API Error: Request timed out. Please check browser console for details.")
        return None
    except requests.RequestException as e:
        _log_error_to_console(str(e))
        st.error("API Error: Request failed. Please check browser console for detailed error information.")
        return None
    except ValueError as e:
        _log_error_to_console(f"Invalid JSON response: {str(e)}")
        st.error("API Error: Invalid JSON response. Please check browser console for detailed error information.")
        return None


def post_api(endpoint, data=None, params=None):
    """Post data to SporeStack API"""
    try:
        response = requests.post(
            f"{API_BASE}{endpoint}",
            json=data,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        _log_error_to_console("Request timed out")
        return {"error": "Request timed out. Check browser console for details.", "success": False}
    except requests.RequestException as e:
        # Log detailed error to console
        error_detail = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_body = e.response.json()
                error_detail = f"{str(e)} - Details: {error_body}"
            except (ValueError, TypeError, AttributeError):
                try:
                    error_detail = f"{str(e)} - Response: {e.response.text}"
                except (AttributeError, TypeError):
                    pass

        _log_error_to_console(error_detail)
        return {"error": "API request failed. Check browser console for detailed error information.", "success": False}
    except ValueError as e:
        _log_error_to_console(f"Invalid JSON response: {str(e)}")
        return {"error": "Invalid JSON response. Check browser console for detailed error information.", "success": False}
