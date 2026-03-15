"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

ConfigKeeper Component Integration Tests

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock
import logging

from phantom.modules.core.lib.config_keeper import ConfigKeeper
from phantom.api.exceptions import ValidationError, ServiceOperationError


class TestConfigKeeper:

    @pytest.fixture
    def mock_dependencies(self):
        """Provide mock dependencies for ConfigKeeper testing."""
        # Setup mock dependencies for ConfigKeeper testing
        config_dir = Path("/tmp/test_config")
        logger = Mock(spec=logging.Logger)
        load_config = Mock()
        save_config = Mock()
        runtime_updater = Mock()

        return {
            "config_dir": config_dir,
            "logger": logger,
            "load_config": load_config,
            "save_config": save_config,
            "runtime_updater": runtime_updater
        }

    @pytest.mark.integration
    def test_retrieve_default_tweaks(self, mock_dependencies):
        """Test retrieving default tweak settings when no tweaks are configured."""
        # Setup mock dependencies with a configuration without tweaks section
        deps = mock_dependencies
        deps["load_config"].return_value = {
            "version": "1.0",
            "server": {"ip": "192.168.1.1"}
        }

        # Initialize ConfigKeeper with mock dependencies
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            deps["runtime_updater"]
        )

        # Retrieve current tweaks to test default values
        result = keeper.retrieve_current_tweaks()

        # Verify default value for restart_service_after_client_creation is False
        assert result["restart_service_after_client_creation"] is False

        # Verify description is included for the tweak setting
        assert "restart_service_after_client_creation_description" in result
        assert "Restart WireGuard service" in result["restart_service_after_client_creation_description"]

        # Ensure configuration was loaded once
        deps["load_config"].assert_called_once()

    @pytest.mark.integration
    def test_retrieve_existing_tweaks(self, mock_dependencies):
        """Test retrieving tweak settings when tweaks are already configured."""
        # Setup mock configuration with existing tweaks section
        deps = mock_dependencies
        deps["load_config"].return_value = {
            "version": "1.0",
            "tweaks": {
                "restart_service_after_client_creation": True
            }
        }

        # Create keeper instance with mock dependencies
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            deps["runtime_updater"]
        )

        # Retrieve current tweaks to verify existing values are returned
        result = keeper.retrieve_current_tweaks()

        # Verify the configured tweak value is returned correctly
        assert result["restart_service_after_client_creation"] is True

        # Call retrieve again to ensure configuration is loaded each time
        keeper.retrieve_current_tweaks()
        assert deps["load_config"].call_count == 2

    @pytest.mark.integration
    def test_apply_tweak_modification_success(self, mock_dependencies):
        """Test successful modification of a tweak setting."""
        # Setup configuration with existing tweak value set to False
        deps = mock_dependencies
        deps["load_config"].return_value = {
            "version": "1.0",
            "tweaks": {
                "restart_service_after_client_creation": False
            }
        }

        # Initialize ConfigKeeper with mock dependencies
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            deps["runtime_updater"]
        )

        # Apply modification to change tweak value from False to True
        result = keeper.apply_tweak_modification(
            "restart_service_after_client_creation",
            True
        )

        # Verify the returned result contains correct information
        assert result["setting"] == "restart_service_after_client_creation"
        assert result["new_value"] is True
        assert result["old_value"] is False
        assert "updated from False to True" in result["message"]

        # Verify configuration was saved with the new value
        deps["save_config"].assert_called_once()
        saved_config = deps["save_config"].call_args[0][0]
        assert saved_config["tweaks"]["restart_service_after_client_creation"] is True

        # Verify runtime updater was called with the new value
        deps["runtime_updater"].assert_called_once_with(
            "restart_service_after_client_creation",
            True
        )

        # Verify info logging was performed
        deps["logger"].info.assert_called()

    @pytest.mark.integration
    def test_invalid_tweak_name_validation(self, mock_dependencies):
        """Test validation error when attempting to modify an invalid tweak name."""
        # Setup ConfigKeeper with mock dependencies
        deps = mock_dependencies
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            deps["runtime_updater"]
        )

        # Attempt to modify an invalid tweak name and expect ValidationError
        with pytest.raises(ValidationError) as exc_info:
            keeper.apply_tweak_modification("invalid_tweak", True)

        # Verify error message contains appropriate information
        error_msg = str(exc_info.value)
        assert "Invalid setting: invalid_tweak" in error_msg
        assert "restart_service_after_client_creation" in error_msg

        # Ensure no configuration operations were performed
        deps["load_config"].assert_not_called()
        deps["save_config"].assert_not_called()

    @pytest.mark.integration
    def test_ensure_tweaks_section_creation(self, mock_dependencies):
        """Test automatic creation of tweaks section when it doesn't exist."""
        # Setup configuration without a tweaks section
        deps = mock_dependencies
        deps["load_config"].return_value = {
            "version": "1.0",
            "server": {"ip": "192.168.1.1"}
        }

        # Initialize ConfigKeeper with mock dependencies
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            deps["runtime_updater"]
        )

        # Apply modification to trigger tweaks section creation
        keeper.apply_tweak_modification(
            "restart_service_after_client_creation",
            True
        )

        # Verify tweaks section was created and contains the new value
        saved_config = deps["save_config"].call_args[0][0]
        assert "tweaks" in saved_config
        assert saved_config["tweaks"]["restart_service_after_client_creation"] is True

        # Verify debug logging about tweaks section creation
        debug_calls = [call[0][0] for call in deps["logger"].debug.call_args_list]
        assert any("Created missing 'tweaks' section" in str(call) for call in debug_calls)

    @pytest.mark.integration
    def test_runtime_updater_called(self, mock_dependencies):
        """Test that runtime updater is called when modifying a tweak."""
        # Setup configuration with empty tweaks section
        deps = mock_dependencies
        deps["load_config"].return_value = {"tweaks": {}}

        # Initialize ConfigKeeper with runtime updater
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            deps["runtime_updater"]
        )

        # Apply modification to trigger runtime update
        keeper.apply_tweak_modification(
            "restart_service_after_client_creation",
            True
        )

        # Verify runtime updater was called with correct parameters
        deps["runtime_updater"].assert_called_once_with(
            "restart_service_after_client_creation",
            True
        )

        # Verify debug logging about runtime update
        debug_calls = deps["logger"].debug.call_args_list
        assert any("Runtime value updated" in str(call) for call in debug_calls)

    @pytest.mark.integration
    def test_runtime_updater_failure_handling(self, mock_dependencies):
        """Test graceful handling when runtime updater fails."""
        # Setup mock to raise an error when runtime updater is called
        deps = mock_dependencies
        deps["load_config"].return_value = {"tweaks": {}}
        deps["runtime_updater"].side_effect = ValueError("Runtime update failed")

        # Initialize ConfigKeeper with failing runtime updater
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            deps["runtime_updater"]
        )

        # Apply modification despite runtime updater failure
        result = keeper.apply_tweak_modification(
            "restart_service_after_client_creation",
            True
        )

        # Verify the configuration is still updated despite runtime failure
        assert result["new_value"] is True

        # Verify warning was logged about runtime update failure
        deps["logger"].warning.assert_called()
        warning_msg = str(deps["logger"].warning.call_args[0][0])
        assert "Failed to update runtime value" in warning_msg

    @pytest.mark.integration
    def test_config_read_error_handling(self, mock_dependencies):
        """Test error handling when configuration read fails."""
        # Setup mock to raise an exception when reading configuration
        deps = mock_dependencies
        deps["load_config"].side_effect = Exception("Config read failed")

        # Initialize ConfigKeeper with mock dependencies
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            deps["runtime_updater"]
        )

        # Attempt to retrieve tweaks and expect ServiceOperationError
        with pytest.raises(ServiceOperationError) as exc_info:
            keeper.retrieve_current_tweaks()

        # Verify error message contains helpful information
        error_msg = str(exc_info.value)
        assert "Unable to retrieve tweak settings" in error_msg
        assert "Configuration file exists" in error_msg

        # Verify error was logged
        deps["logger"].error.assert_called_with("Failed to retrieve tweak settings")

    @pytest.mark.integration
    def test_config_save_error_handling(self, mock_dependencies):
        """Test error handling when configuration save fails."""
        # Setup mock to raise an exception when saving configuration
        deps = mock_dependencies
        deps["load_config"].return_value = {"tweaks": {}}
        deps["save_config"].side_effect = Exception("Save failed")

        # Initialize ConfigKeeper with mock dependencies
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            deps["runtime_updater"]
        )

        # Attempt to apply modification and expect ServiceOperationError
        with pytest.raises(ServiceOperationError) as exc_info:
            keeper.apply_tweak_modification(
                "restart_service_after_client_creation",
                True
            )

        # Verify error message provides helpful information
        error_msg = str(exc_info.value)
        assert "Unable to update tweak setting" in error_msg
        assert "Configuration file is read-only" in error_msg

        # Verify error was logged
        deps["logger"].error.assert_called()

    @pytest.mark.integration
    def test_validate_tweak_name_method(self, mock_dependencies):
        """Test validation of tweak names to ensure only valid names are accepted."""
        # Initialize ConfigKeeper without runtime updater for validation testing
        deps = mock_dependencies
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            None
        )

        # Test valid tweak name is accepted
        assert keeper.validate_tweak_name("restart_service_after_client_creation") is True

        # Test various invalid tweak names are rejected
        assert keeper.validate_tweak_name("invalid_tweak") is False
        assert keeper.validate_tweak_name("") is False
        assert keeper.validate_tweak_name("random_setting") is False

    @pytest.mark.integration
    def test_ensure_tweaks_section_exists_method(self, mock_dependencies):
        """Test the ensure_tweaks_section_exists helper method."""
        # Initialize ConfigKeeper without runtime updater
        deps = mock_dependencies
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            None
        )

        # Test creating tweaks section when it doesn't exist
        config = {"version": "1.0"}
        updated = keeper.ensure_tweaks_section_exists(config)

        # Verify tweaks section was created as empty dict
        assert "tweaks" in updated
        assert updated["tweaks"] == {}

        # Test preserving existing tweaks section
        config_with_tweaks = {"tweaks": {"existing": True}}
        result = keeper.ensure_tweaks_section_exists(config_with_tweaks)

        # Verify existing tweaks section is preserved
        assert result["tweaks"]["existing"] is True

    @pytest.mark.integration
    def test_empty_config_handling(self, mock_dependencies):
        """Test handling of completely empty configuration."""
        # Setup mock to return empty configuration
        deps = mock_dependencies
        deps["load_config"].return_value = {}

        # Initialize ConfigKeeper with empty config
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            deps["runtime_updater"]
        )

        # Retrieve tweaks from empty config should return defaults
        result = keeper.retrieve_current_tweaks()
        assert result["restart_service_after_client_creation"] is False

    @pytest.mark.integration
    def test_none_runtime_updater(self, mock_dependencies):
        """Test modification when runtime updater is None."""
        # Setup configuration with tweaks section
        deps = mock_dependencies
        deps["load_config"].return_value = {"tweaks": {}}

        # Initialize ConfigKeeper without runtime updater
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            None  # No runtime updater
        )

        # Apply modification without runtime updater
        result = keeper.apply_tweak_modification(
            "restart_service_after_client_creation",
            True
        )

        # Verify modification succeeds without runtime updater
        assert result["new_value"] is True
        deps["save_config"].assert_called_once()

    @pytest.mark.integration
    def test_same_value_update(self, mock_dependencies):
        """Test updating a tweak to the same value it already has."""
        # Setup configuration with tweak already set to True
        deps = mock_dependencies
        deps["load_config"].return_value = {
            "tweaks": {"restart_service_after_client_creation": True}
        }

        # Initialize ConfigKeeper with mock dependencies
        keeper = ConfigKeeper(
            deps["config_dir"],
            deps["logger"],
            deps["load_config"],
            deps["save_config"],
            deps["runtime_updater"]
        )

        # Apply modification with same value
        result = keeper.apply_tweak_modification(
            "restart_service_after_client_creation",
            True
        )

        # Verify update is processed even when value doesn't change
        assert result["old_value"] is True
        assert result["new_value"] is True
        assert "updated from True to True" in result["message"]

        # Verify save is still called even for same value
        deps["save_config"].assert_called_once()
