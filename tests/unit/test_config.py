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
