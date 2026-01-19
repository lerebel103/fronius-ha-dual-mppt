"""Unit tests for configuration management."""

import os
import tempfile

import pytest
import yaml

from fronius_modbus.config import Config, ConfigValidationError


class TestConfigLoading:
    """Test configuration file loading."""

    def test_load_valid_config(self) -> None:
        """Test loading a valid configuration file."""
        config_data = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 502,
                "unit_id": 1,
                "timeout": 10,
            },
            "mqtt": {
                "broker": "192.168.1.50",
                "port": 1883,
                "username": "homeassistant",
                "password": "secret",
                "client_id": "fronius_bridge",
                "topic_prefix": "homeassistant",
            },
            "application": {
                "poll_interval": 5,
                "mqtt_republish_rate": 300,
                "logging": {
                    "level": "INFO",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = Config(config_path)

            # Verify Modbus properties
            assert config.modbus_host == "192.168.1.100"
            assert config.modbus_port == 502
            assert config.modbus_unit_id == 1
            assert config.modbus_timeout == 10

            # Verify MQTT properties
            assert config.mqtt_broker == "192.168.1.50"
            assert config.mqtt_port == 1883
            assert config.mqtt_username == "homeassistant"
            assert config.mqtt_password == "secret"
            assert config.mqtt_client_id == "fronius_bridge"
            assert config.mqtt_topic_prefix == "homeassistant"

            # Verify Application properties
            assert config.poll_interval == 5
            assert config.log_level == "INFO"
        finally:
            os.unlink(config_path)

    def test_file_not_found(self) -> None:
        """Test error when config file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            Config("/nonexistent/path/config.yaml")

    def test_empty_config_file(self) -> None:
        """Test error when config file is empty."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            config_path = f.name

        try:
            with pytest.raises(yaml.YAMLError, match="Configuration file is empty"):
                Config(config_path)
        finally:
            os.unlink(config_path)


class TestConfigValidation:
    """Test configuration validation."""

    def test_missing_modbus_section(self) -> None:
        """Test error when modbus section is missing."""
        config_data = {
            "mqtt": {
                "broker": "192.168.1.50",
                "port": 1883,
                "username": "user",
                "password": "pass",
                "client_id": "client",
                "topic_prefix": "homeassistant",
            },
            "application": {
                "poll_interval": 5,
                "log_level": "INFO",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(ConfigValidationError, match="Missing required section: 'modbus'"):
                Config(config_path)
        finally:
            os.unlink(config_path)

    def test_missing_mqtt_section(self) -> None:
        """Test error when mqtt section is missing."""
        config_data = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 502,
                "unit_id": 1,
                "timeout": 10,
            },
            "application": {
                "poll_interval": 5,
                "log_level": "INFO",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(ConfigValidationError, match="Missing required section: 'mqtt'"):
                Config(config_path)
        finally:
            os.unlink(config_path)

    def test_missing_application_section(self) -> None:
        """Test error when application section is missing."""
        config_data = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 502,
                "unit_id": 1,
                "timeout": 10,
            },
            "mqtt": {
                "broker": "192.168.1.50",
                "port": 1883,
                "username": "user",
                "password": "pass",
                "client_id": "client",
                "topic_prefix": "homeassistant",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(
                ConfigValidationError, match="Missing required section: 'application'"
            ):
                Config(config_path)
        finally:
            os.unlink(config_path)

    def test_invalid_modbus_port(self) -> None:
        """Test error when modbus port is out of range."""
        config_data = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 70000,  # Invalid port
                "unit_id": 1,
                "timeout": 10,
            },
            "mqtt": {
                "broker": "192.168.1.50",
                "port": 1883,
                "username": "user",
                "password": "pass",
                "client_id": "client",
                "topic_prefix": "homeassistant",
            },
            "application": {
                "poll_interval": 5,
                "log_level": "INFO",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(
                ConfigValidationError, match="modbus.port must be between 1 and 65535"
            ):
                Config(config_path)
        finally:
            os.unlink(config_path)

    def test_invalid_log_level(self) -> None:
        """Test error when log level is invalid."""
        config_data = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 502,
                "unit_id": 1,
                "timeout": 10,
            },
            "mqtt": {
                "broker": "192.168.1.50",
                "port": 1883,
                "username": "user",
                "password": "pass",
                "client_id": "client",
                "topic_prefix": "homeassistant",
            },
            "application": {
                "poll_interval": 5,
                "mqtt_republish_rate": 300,
                "logging": {
                    "level": "INVALID",  # Invalid log level
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(
                ConfigValidationError,
                match="application.logging.level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL",
            ):
                Config(config_path)
        finally:
            os.unlink(config_path)

    def test_missing_modbus_host(self) -> None:
        """Test error when modbus host is missing."""
        config_data = {
            "modbus": {
                "port": 502,
                "unit_id": 1,
                "timeout": 10,
            },
            "mqtt": {
                "broker": "192.168.1.50",
                "port": 1883,
                "username": "user",
                "password": "pass",
                "client_id": "client",
                "topic_prefix": "homeassistant",
            },
            "application": {
                "poll_interval": 5,
                "log_level": "INFO",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(ConfigValidationError, match="modbus.host is required"):
                Config(config_path)
        finally:
            os.unlink(config_path)

    def test_negative_poll_interval(self) -> None:
        """Test error when poll interval is negative."""
        config_data = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 502,
                "unit_id": 1,
                "timeout": 10,
            },
            "mqtt": {
                "broker": "192.168.1.50",
                "port": 1883,
                "username": "user",
                "password": "pass",
                "client_id": "client",
                "topic_prefix": "homeassistant",
            },
            "application": {
                "poll_interval": -5,  # Invalid negative value
                "log_level": "INFO",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(
                ConfigValidationError, match="application.poll_interval must be greater than 0"
            ):
                Config(config_path)
        finally:
            os.unlink(config_path)


class TestDiagnosticSensorConfig:
    """Test diagnostic sensor configuration."""

    def test_diagnostic_sensors_defaults(self) -> None:
        """Test that diagnostic sensor configuration uses sensible defaults when section is missing."""
        config_data = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 502,
                "unit_id": 1,
                "timeout": 10,
            },
            "mqtt": {
                "broker": "192.168.1.50",
                "port": 1883,
                "username": "homeassistant",
                "password": "secret",
                "client_id": "fronius_bridge",
                "topic_prefix": "homeassistant",
            },
            "application": {
                "poll_interval": 5,
                "mqtt_republish_rate": 300,
                "logging": {
                    "level": "INFO",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            # No diagnostic_sensors section - should use defaults
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = Config(config_path)

            # Verify default values
            assert config.diagnostic_sensors_enabled is True
            assert config.temperature_sensors_enabled is True
            assert config.temperature_sensors_default_enabled is False
            assert config.operating_state_sensors_enabled is True
            assert config.operating_state_sensors_default_enabled is True
            assert config.module_events_sensors_enabled is True
            assert config.module_events_sensors_default_enabled is False
        finally:
            os.unlink(config_path)

    def test_diagnostic_sensors_custom_config(self) -> None:
        """Test diagnostic sensor configuration with custom values."""
        config_data = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 502,
                "unit_id": 1,
                "timeout": 10,
            },
            "mqtt": {
                "broker": "192.168.1.50",
                "port": 1883,
                "username": "homeassistant",
                "password": "secret",
                "client_id": "fronius_bridge",
                "topic_prefix": "homeassistant",
            },
            "application": {
                "poll_interval": 5,
                "mqtt_republish_rate": 300,
                "logging": {
                    "level": "INFO",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            "diagnostic_sensors": {
                "enabled": False,
                "temperature": {
                    "enabled": False,
                    "enabled_by_default": True,
                },
                "operating_state": {
                    "enabled": True,
                    "enabled_by_default": False,
                },
                "module_events": {
                    "enabled": False,
                    "enabled_by_default": True,
                },
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = Config(config_path)

            # Verify custom values
            assert config.diagnostic_sensors_enabled is False
            assert config.temperature_sensors_enabled is False
            assert config.temperature_sensors_default_enabled is True
            assert config.operating_state_sensors_enabled is True
            assert config.operating_state_sensors_default_enabled is False
            assert config.module_events_sensors_enabled is False
            assert config.module_events_sensors_default_enabled is True
        finally:
            os.unlink(config_path)

    def test_invalid_diagnostic_sensors_enabled(self) -> None:
        """Test error when diagnostic_sensors.enabled is not a boolean."""
        config_data = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 502,
                "unit_id": 1,
                "timeout": 10,
            },
            "mqtt": {
                "broker": "192.168.1.50",
                "port": 1883,
                "username": "homeassistant",
                "password": "secret",
                "client_id": "fronius_bridge",
                "topic_prefix": "homeassistant",
            },
            "application": {
                "poll_interval": 5,
                "mqtt_republish_rate": 300,
                "logging": {
                    "level": "INFO",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            "diagnostic_sensors": {
                "enabled": "invalid",  # Should be boolean
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(
                ConfigValidationError, match="diagnostic_sensors.enabled must be a boolean"
            ):
                Config(config_path)
        finally:
            os.unlink(config_path)

    def test_invalid_temperature_config(self) -> None:
        """Test error when temperature configuration is invalid."""
        config_data = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 502,
                "unit_id": 1,
                "timeout": 10,
            },
            "mqtt": {
                "broker": "192.168.1.50",
                "port": 1883,
                "username": "homeassistant",
                "password": "secret",
                "client_id": "fronius_bridge",
                "topic_prefix": "homeassistant",
            },
            "application": {
                "poll_interval": 5,
                "mqtt_republish_rate": 300,
                "logging": {
                    "level": "INFO",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            "diagnostic_sensors": {
                "temperature": "invalid",  # Should be dictionary
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(
                ConfigValidationError, match="diagnostic_sensors.temperature must be a dictionary"
            ):
                Config(config_path)
        finally:
            os.unlink(config_path)

    def test_invalid_temperature_enabled_by_default(self) -> None:
        """Test error when temperature enabled_by_default is not a boolean."""
        config_data = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 502,
                "unit_id": 1,
                "timeout": 10,
            },
            "mqtt": {
                "broker": "192.168.1.50",
                "port": 1883,
                "username": "homeassistant",
                "password": "secret",
                "client_id": "fronius_bridge",
                "topic_prefix": "homeassistant",
            },
            "application": {
                "poll_interval": 5,
                "mqtt_republish_rate": 300,
                "logging": {
                    "level": "INFO",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            "diagnostic_sensors": {
                "temperature": {
                    "enabled_by_default": "invalid",  # Should be boolean
                },
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(
                ConfigValidationError, match="diagnostic_sensors.temperature.enabled_by_default must be a boolean"
            ):
                Config(config_path)
        finally:
            os.unlink(config_path)

    def test_partial_diagnostic_config(self) -> None:
        """Test that partial diagnostic configuration works with defaults for missing parts."""
        config_data = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 502,
                "unit_id": 1,
                "timeout": 10,
            },
            "mqtt": {
                "broker": "192.168.1.50",
                "port": 1883,
                "username": "homeassistant",
                "password": "secret",
                "client_id": "fronius_bridge",
                "topic_prefix": "homeassistant",
            },
            "application": {
                "poll_interval": 5,
                "mqtt_republish_rate": 300,
                "logging": {
                    "level": "INFO",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            "diagnostic_sensors": {
                "enabled": False,
                "temperature": {
                    "enabled": False,
                    # enabled_by_default missing - should use default
                },
                # operating_state and module_events missing - should use defaults
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = Config(config_path)

            # Verify mixed custom and default values
            assert config.diagnostic_sensors_enabled is False
            assert config.temperature_sensors_enabled is False
            assert config.temperature_sensors_default_enabled is False  # Default
            assert config.operating_state_sensors_enabled is True  # Default
            assert config.operating_state_sensors_default_enabled is True  # Default
            assert config.module_events_sensors_enabled is True  # Default
            assert config.module_events_sensors_default_enabled is False  # Default
        finally:
            os.unlink(config_path)
