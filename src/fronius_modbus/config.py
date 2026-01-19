"""Configuration management for Fronius Modbus to MQTT bridge."""

import os
from typing import Any, Dict, List

import yaml


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


class Config:
    """Load and validate YAML configuration for the Fronius Modbus bridge."""

    def __init__(self, config_path: str) -> None:
        """
        Initialize Config by loading from file path.

        Args:
            config_path: Path to YAML configuration file

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is malformed
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            self._config: Dict[str, Any] = yaml.safe_load(f)

        if self._config is None:
            raise yaml.YAMLError("Configuration file is empty")

        # Validate configuration on initialization
        self.validate()

    def validate(self) -> bool:
        """
        Validate all configuration parameters.

        Returns:
            True if validation passes

        Raises:
            ConfigValidationError: If any validation fails with descriptive message
        """
        errors: List[str] = []

        # Validate Modbus section
        if "modbus" not in self._config:
            errors.append("Missing required section: 'modbus'")
        else:
            modbus = self._config["modbus"]
            errors.extend(self._validate_modbus(modbus))

        # Validate MQTT section
        if "mqtt" not in self._config:
            errors.append("Missing required section: 'mqtt'")
        else:
            mqtt = self._config["mqtt"]
            errors.extend(self._validate_mqtt(mqtt))

        # Validate Application section
        if "application" not in self._config:
            errors.append("Missing required section: 'application'")
        else:
            application = self._config["application"]
            errors.extend(self._validate_application(application))

        # Validate Diagnostic Sensors section (optional)
        if "diagnostic_sensors" in self._config:
            diagnostic_sensors = self._config["diagnostic_sensors"]
            errors.extend(self._validate_diagnostic_sensors(diagnostic_sensors))

        if errors:
            raise ConfigValidationError(
                "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )

        return True

    def _validate_modbus(self, modbus: Dict[str, Any]) -> List[str]:
        """Validate Modbus configuration section."""
        errors: List[str] = []

        # Validate host
        if "host" not in modbus:
            errors.append("modbus.host is required")
        elif not isinstance(modbus["host"], str):
            errors.append("modbus.host must be a string")
        elif not modbus["host"].strip():
            errors.append("modbus.host cannot be empty")

        # Validate port
        if "port" not in modbus:
            errors.append("modbus.port is required")
        elif not isinstance(modbus["port"], int):
            errors.append("modbus.port must be an integer")
        elif not (1 <= modbus["port"] <= 65535):
            errors.append("modbus.port must be between 1 and 65535")

        # Validate unit_id
        if "unit_id" not in modbus:
            errors.append("modbus.unit_id is required")
        elif not isinstance(modbus["unit_id"], int):
            errors.append("modbus.unit_id must be an integer")
        elif not (0 <= modbus["unit_id"] <= 255):
            errors.append("modbus.unit_id must be between 0 and 255")

        # Validate timeout
        if "timeout" not in modbus:
            errors.append("modbus.timeout is required")
        elif not isinstance(modbus["timeout"], int):
            errors.append("modbus.timeout must be an integer")
        elif modbus["timeout"] <= 0:
            errors.append("modbus.timeout must be greater than 0")

        return errors

    def _validate_mqtt(self, mqtt: Dict[str, Any]) -> List[str]:
        """Validate MQTT configuration section."""
        errors: List[str] = []

        # Validate broker
        if "broker" not in mqtt:
            errors.append("mqtt.broker is required")
        elif not isinstance(mqtt["broker"], str):
            errors.append("mqtt.broker must be a string")
        elif not mqtt["broker"].strip():
            errors.append("mqtt.broker cannot be empty")

        # Validate port
        if "port" not in mqtt:
            errors.append("mqtt.port is required")
        elif not isinstance(mqtt["port"], int):
            errors.append("mqtt.port must be an integer")
        elif not (1 <= mqtt["port"] <= 65535):
            errors.append("mqtt.port must be between 1 and 65535")

        # Validate username
        if "username" not in mqtt:
            errors.append("mqtt.username is required")
        elif not isinstance(mqtt["username"], str):
            errors.append("mqtt.username must be a string")

        # Validate password
        if "password" not in mqtt:
            errors.append("mqtt.password is required")
        elif not isinstance(mqtt["password"], str):
            errors.append("mqtt.password must be a string")

        # Validate client_id
        if "client_id" not in mqtt:
            errors.append("mqtt.client_id is required")
        elif not isinstance(mqtt["client_id"], str):
            errors.append("mqtt.client_id must be a string")
        elif not mqtt["client_id"].strip():
            errors.append("mqtt.client_id cannot be empty")

        # Validate topic_prefix
        if "topic_prefix" not in mqtt:
            errors.append("mqtt.topic_prefix is required")
        elif not isinstance(mqtt["topic_prefix"], str):
            errors.append("mqtt.topic_prefix must be a string")
        elif not mqtt["topic_prefix"].strip():
            errors.append("mqtt.topic_prefix cannot be empty")

        return errors

    def _validate_application(self, application: Dict[str, Any]) -> List[str]:
        """Validate Application configuration section."""
        errors: List[str] = []

        # Validate poll_interval
        if "poll_interval" not in application:
            errors.append("application.poll_interval is required")
        elif not isinstance(application["poll_interval"], int):
            errors.append("application.poll_interval must be an integer")
        elif application["poll_interval"] <= 0:
            errors.append("application.poll_interval must be greater than 0")

        # Validate mqtt_republish_rate (requirement 10.8)
        if "mqtt_republish_rate" not in application:
            errors.append("application.mqtt_republish_rate is required")
        elif not isinstance(application["mqtt_republish_rate"], int):
            errors.append("application.mqtt_republish_rate must be an integer")
        elif application["mqtt_republish_rate"] <= 0:
            errors.append("application.mqtt_republish_rate must be greater than 0")

        # Validate logging configuration (requirement 10.6)
        if "logging" not in application:
            errors.append("application.logging is required")
        elif not isinstance(application["logging"], dict):
            errors.append("application.logging must be a dictionary")
        else:
            logging_config = application["logging"]
            
            # Validate log level
            if "level" not in logging_config:
                errors.append("application.logging.level is required")
            elif not isinstance(logging_config["level"], str):
                errors.append("application.logging.level must be a string")
            else:
                valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                if logging_config["level"].upper() not in valid_levels:
                    errors.append(f"application.logging.level must be one of: {', '.join(valid_levels)}")
            
            # Validate log format
            if "format" not in logging_config:
                errors.append("application.logging.format is required")
            elif not isinstance(logging_config["format"], str):
                errors.append("application.logging.format must be a string")
            elif not logging_config["format"].strip():
                errors.append("application.logging.format cannot be empty")

        return errors

    def _validate_diagnostic_sensors(self, diagnostic_sensors: Dict[str, Any]) -> List[str]:
        """Validate Diagnostic Sensors configuration section."""
        errors: List[str] = []

        # Validate global enabled flag
        if "enabled" in diagnostic_sensors:
            if not isinstance(diagnostic_sensors["enabled"], bool):
                errors.append("diagnostic_sensors.enabled must be a boolean")

        # Validate temperature sensor configuration
        if "temperature" in diagnostic_sensors:
            temp_config = diagnostic_sensors["temperature"]
            if not isinstance(temp_config, dict):
                errors.append("diagnostic_sensors.temperature must be a dictionary")
            else:
                if "enabled" in temp_config and not isinstance(temp_config["enabled"], bool):
                    errors.append("diagnostic_sensors.temperature.enabled must be a boolean")
                if "enabled_by_default" in temp_config and not isinstance(temp_config["enabled_by_default"], bool):
                    errors.append("diagnostic_sensors.temperature.enabled_by_default must be a boolean")

        # Validate operating state sensor configuration
        if "operating_state" in diagnostic_sensors:
            state_config = diagnostic_sensors["operating_state"]
            if not isinstance(state_config, dict):
                errors.append("diagnostic_sensors.operating_state must be a dictionary")
            else:
                if "enabled" in state_config and not isinstance(state_config["enabled"], bool):
                    errors.append("diagnostic_sensors.operating_state.enabled must be a boolean")
                if "enabled_by_default" in state_config and not isinstance(state_config["enabled_by_default"], bool):
                    errors.append("diagnostic_sensors.operating_state.enabled_by_default must be a boolean")

        # Validate module events sensor configuration
        if "module_events" in diagnostic_sensors:
            events_config = diagnostic_sensors["module_events"]
            if not isinstance(events_config, dict):
                errors.append("diagnostic_sensors.module_events must be a dictionary")
            else:
                if "enabled" in events_config and not isinstance(events_config["enabled"], bool):
                    errors.append("diagnostic_sensors.module_events.enabled must be a boolean")
                if "enabled_by_default" in events_config and not isinstance(events_config["enabled_by_default"], bool):
                    errors.append("diagnostic_sensors.module_events.enabled_by_default must be a boolean")

        return errors

    # Modbus properties
    @property
    def modbus_host(self) -> str:
        """Get Modbus host address."""
        return self._config["modbus"]["host"]

    @property
    def modbus_port(self) -> int:
        """Get Modbus port."""
        return self._config["modbus"]["port"]

    @property
    def modbus_unit_id(self) -> int:
        """Get Modbus unit ID."""
        return self._config["modbus"]["unit_id"]

    @property
    def modbus_timeout(self) -> int:
        """Get Modbus timeout in seconds."""
        return self._config["modbus"]["timeout"]

    # MQTT properties
    @property
    def mqtt_broker(self) -> str:
        """Get MQTT broker address."""
        return self._config["mqtt"]["broker"]

    @property
    def mqtt_port(self) -> int:
        """Get MQTT port."""
        return self._config["mqtt"]["port"]

    @property
    def mqtt_username(self) -> str:
        """Get MQTT username."""
        return self._config["mqtt"]["username"]

    @property
    def mqtt_password(self) -> str:
        """Get MQTT password."""
        return self._config["mqtt"]["password"]

    @property
    def mqtt_client_id(self) -> str:
        """Get MQTT client ID."""
        return self._config["mqtt"]["client_id"]

    @property
    def mqtt_topic_prefix(self) -> str:
        """Get MQTT topic prefix."""
        return self._config["mqtt"]["topic_prefix"]

    # Application properties
    @property
    def poll_interval(self) -> int:
        """Get polling interval in seconds."""
        return self._config["application"]["poll_interval"]

    @property
    def mqtt_republish_rate(self) -> int:
        """Get MQTT republish rate in seconds."""
        return self._config["application"]["mqtt_republish_rate"]

    @property
    def log_level(self) -> str:
        """Get log level."""
        return self._config["application"]["logging"]["level"].upper()

    @property
    def log_format(self) -> str:
        """Get log format string."""
        return self._config["application"]["logging"]["format"]

    # Diagnostic Sensors properties
    @property
    def diagnostic_sensors_enabled(self) -> bool:
        """Get global diagnostic sensors enabled flag."""
        return self._config.get("diagnostic_sensors", {}).get("enabled", True)

    @property
    def temperature_sensors_enabled(self) -> bool:
        """Get temperature sensors enabled flag."""
        return self._config.get("diagnostic_sensors", {}).get("temperature", {}).get("enabled", True)

    @property
    def temperature_sensors_default_enabled(self) -> bool:
        """Get temperature sensors default enabled flag."""
        return self._config.get("diagnostic_sensors", {}).get("temperature", {}).get("enabled_by_default", False)

    @property
    def operating_state_sensors_enabled(self) -> bool:
        """Get operating state sensors enabled flag."""
        return self._config.get("diagnostic_sensors", {}).get("operating_state", {}).get("enabled", True)

    @property
    def operating_state_sensors_default_enabled(self) -> bool:
        """Get operating state sensors default enabled flag."""
        return self._config.get("diagnostic_sensors", {}).get("operating_state", {}).get("enabled_by_default", True)

    @property
    def module_events_sensors_enabled(self) -> bool:
        """Get module events sensors enabled flag."""
        return self._config.get("diagnostic_sensors", {}).get("module_events", {}).get("enabled", True)

    @property
    def module_events_sensors_default_enabled(self) -> bool:
        """Get module events sensors default enabled flag."""
        return self._config.get("diagnostic_sensors", {}).get("module_events", {}).get("enabled_by_default", False)
