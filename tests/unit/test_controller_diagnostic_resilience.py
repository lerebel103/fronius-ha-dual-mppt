"""
Tests for controller resilience when diagnostic sensors fail.
"""

import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

import pytest

from fronius_modbus.config import Config
from fronius_modbus.controller import FroniusBridgeController, handle_data_polling, ConnectionState
from fronius_modbus.modbus_client import MPPTData, MPPTChannelData, DiagnosticData, MPPTModuleData
from fronius_modbus.mqtt_publisher import MQTTPublisher


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    config_content = """
modbus:
  host: "192.168.1.100"
  port: 502
  unit_id: 1
  timeout: 10

mqtt:
  broker: "192.168.1.50"
  port: 1883
  username: "test"
  password: "test"
  client_id: "test_client"
  topic_prefix: "homeassistant"

application:
  poll_interval: 5
  mqtt_republish_rate: 300
  logging:
    level: "INFO"
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

diagnostic_sensors:
  enabled: true
  temperature:
    enabled: true
    enabled_by_default: false
  operating_state:
    enabled: true
    enabled_by_default: true
  module_events:
    enabled: true
    enabled_by_default: false
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config = Config(f.name)
        os.unlink(f.name)
        return config


class TestControllerDiagnosticResilience:
    """Test controller resilience when diagnostic sensors fail."""

    def test_diagnostic_discovery_failure_doesnt_affect_core_functionality(self, sample_config):
        """Test that diagnostic discovery failures don't prevent core sensor operation."""
        # Create mocks
        mock_modbus_client = Mock()
        mock_mqtt_publisher = Mock()
        
        # Set up connection state
        state = ConnectionState()
        state.modbus_connected = True
        state.model_160_verified = True
        state.mqtt_connected = True
        state.device_info = {"manufacturer": "Fronius", "model": "Symo", "serial_number": "12345"}
        
        # Create sample MPPT data with diagnostic data
        mppt_data = MPPTData(
            mppt1=MPPTChannelData(voltage=400.5, current=10.2, power=4085.1),
            mppt2=MPPTChannelData(voltage=395.3, current=9.8, power=3873.94),
            total_power=7959.04,
            timestamp=Mock(),
            modules=[
                MPPTModuleData(
                    voltage=400.5, current=10.2, power=4085.1,
                    diagnostics=DiagnosticData.create(45.2, 4, 0)
                ),
                MPPTModuleData(
                    voltage=395.3, current=9.8, power=3873.94,
                    diagnostics=DiagnosticData.create(42.1, 4, 0)
                )
            ]
        )
        
        # Mock successful MPPT data read
        mock_modbus_client.read_mppt_data.return_value = mppt_data
        
        # Mock successful core sensor publishing but failed diagnostic discovery
        mock_mqtt_publisher.publish_sensor_data.return_value = True
        mock_mqtt_publisher.publish_diagnostic_discovery.return_value = False  # Diagnostic discovery fails
        mock_mqtt_publisher.publish_diagnostic_data.return_value = True
        mock_mqtt_publisher.is_connected.return_value = True
        
        # Call data polling
        handle_data_polling(mock_modbus_client, mock_mqtt_publisher, state, sample_config)
        
        # Verify core sensor data was published despite diagnostic discovery failure
        mock_mqtt_publisher.publish_sensor_data.assert_called_once_with(mppt_data)
        
        # Verify diagnostic data was still attempted to be published
        mock_mqtt_publisher.publish_diagnostic_data.assert_called_once()
        
        # Verify connection state remains healthy
        assert state.modbus_connected is True
        assert state.mqtt_connected is True

    def test_diagnostic_data_publish_failure_doesnt_affect_core_sensors(self, sample_config):
        """Test that diagnostic data publishing failures don't affect core sensor publishing."""
        # Create mocks
        mock_modbus_client = Mock()
        mock_mqtt_publisher = Mock()
        
        # Set up connection state
        state = ConnectionState()
        state.modbus_connected = True
        state.model_160_verified = True
        state.mqtt_connected = True
        state.device_info = {"manufacturer": "Fronius", "model": "Symo", "serial_number": "12345"}
        state.diagnostic_discovery_published = True  # Already published
        
        # Create sample MPPT data with diagnostic data
        mppt_data = MPPTData(
            mppt1=MPPTChannelData(voltage=400.5, current=10.2, power=4085.1),
            mppt2=MPPTChannelData(voltage=395.3, current=9.8, power=3873.94),
            total_power=7959.04,
            timestamp=Mock(),
            modules=[
                MPPTModuleData(
                    voltage=400.5, current=10.2, power=4085.1,
                    diagnostics=DiagnosticData.create(45.2, 4, 0)
                )
            ]
        )
        
        # Mock successful MPPT data read
        mock_modbus_client.read_mppt_data.return_value = mppt_data
        
        # Mock successful core sensor publishing but failed diagnostic data publishing
        mock_mqtt_publisher.publish_sensor_data.return_value = True
        mock_mqtt_publisher.publish_diagnostic_data.return_value = False  # Diagnostic data fails
        mock_mqtt_publisher.is_connected.return_value = True
        
        # Call data polling
        handle_data_polling(mock_modbus_client, mock_mqtt_publisher, state, sample_config)
        
        # Verify core sensor data was published
        mock_mqtt_publisher.publish_sensor_data.assert_called_once_with(mppt_data)
        
        # Verify diagnostic data publishing was attempted
        mock_mqtt_publisher.publish_diagnostic_data.assert_called_once()
        
        # Verify MQTT connection is not marked as failed for diagnostic failures
        assert state.mqtt_connected is True

    def test_no_diagnostic_modules_doesnt_break_core_functionality(self, sample_config):
        """Test that missing diagnostic modules don't break core functionality."""
        # Create mocks
        mock_modbus_client = Mock()
        mock_mqtt_publisher = Mock()
        
        # Set up connection state
        state = ConnectionState()
        state.modbus_connected = True
        state.model_160_verified = True
        state.mqtt_connected = True
        state.device_info = {"manufacturer": "Fronius", "model": "Symo", "serial_number": "12345"}
        
        # Create MPPT data without diagnostic modules
        mppt_data = MPPTData(
            mppt1=MPPTChannelData(voltage=400.5, current=10.2, power=4085.1),
            mppt2=MPPTChannelData(voltage=395.3, current=9.8, power=3873.94),
            total_power=7959.04,
            timestamp=Mock(),
            modules=None  # No diagnostic modules
        )
        
        # Mock successful MPPT data read
        mock_modbus_client.read_mppt_data.return_value = mppt_data
        
        # Mock successful core sensor publishing
        mock_mqtt_publisher.publish_sensor_data.return_value = True
        mock_mqtt_publisher.is_connected.return_value = True
        
        # Call data polling
        handle_data_polling(mock_modbus_client, mock_mqtt_publisher, state, sample_config)
        
        # Verify core sensor data was published
        mock_mqtt_publisher.publish_sensor_data.assert_called_once_with(mppt_data)
        
        # Verify diagnostic data publishing was not attempted (no modules)
        mock_mqtt_publisher.publish_diagnostic_data.assert_not_called()
        
        # Verify connection state remains healthy
        assert state.modbus_connected is True
        assert state.mqtt_connected is True

    def test_diagnostic_sensors_disabled_in_config(self, sample_config):
        """Test that disabling diagnostic sensors in config prevents their processing."""
        # Modify config to disable diagnostic sensors
        sample_config._config["diagnostic_sensors"]["enabled"] = False
        
        # Create mocks
        mock_modbus_client = Mock()
        mock_mqtt_publisher = Mock()
        
        # Set up connection state
        state = ConnectionState()
        state.modbus_connected = True
        state.model_160_verified = True
        state.mqtt_connected = True
        state.device_info = {"manufacturer": "Fronius", "model": "Symo", "serial_number": "12345"}
        
        # Create sample MPPT data with diagnostic data
        mppt_data = MPPTData(
            mppt1=MPPTChannelData(voltage=400.5, current=10.2, power=4085.1),
            mppt2=MPPTChannelData(voltage=395.3, current=9.8, power=3873.94),
            total_power=7959.04,
            timestamp=Mock(),
            modules=[
                MPPTModuleData(
                    voltage=400.5, current=10.2, power=4085.1,
                    diagnostics=DiagnosticData.create(45.2, 4, 0)
                )
            ]
        )
        
        # Mock successful MPPT data read
        mock_modbus_client.read_mppt_data.return_value = mppt_data
        
        # Mock successful core sensor publishing
        mock_mqtt_publisher.publish_sensor_data.return_value = True
        mock_mqtt_publisher.is_connected.return_value = True
        
        # Call data polling
        handle_data_polling(mock_modbus_client, mock_mqtt_publisher, state, sample_config)
        
        # Verify core sensor data was published
        mock_mqtt_publisher.publish_sensor_data.assert_called_once_with(mppt_data)
        
        # Verify diagnostic data publishing was not attempted (disabled in config)
        mock_mqtt_publisher.publish_diagnostic_data.assert_not_called()
        
        # Verify diagnostic discovery was not attempted
        mock_mqtt_publisher.publish_diagnostic_discovery.assert_not_called()

    def test_empty_diagnostic_modules_list(self, sample_config):
        """Test that empty diagnostic modules list is handled gracefully."""
        # Create mocks
        mock_modbus_client = Mock()
        mock_mqtt_publisher = Mock()
        
        # Set up connection state
        state = ConnectionState()
        state.modbus_connected = True
        state.model_160_verified = True
        state.mqtt_connected = True
        state.device_info = {"manufacturer": "Fronius", "model": "Symo", "serial_number": "12345"}
        
        # Create MPPT data with empty diagnostic modules list
        mppt_data = MPPTData(
            mppt1=MPPTChannelData(voltage=400.5, current=10.2, power=4085.1),
            mppt2=MPPTChannelData(voltage=395.3, current=9.8, power=3873.94),
            total_power=7959.04,
            timestamp=Mock(),
            modules=[]  # Empty list
        )
        
        # Mock successful MPPT data read
        mock_modbus_client.read_mppt_data.return_value = mppt_data
        
        # Mock successful core sensor publishing
        mock_mqtt_publisher.publish_sensor_data.return_value = True
        mock_mqtt_publisher.is_connected.return_value = True
        
        # Call data polling
        handle_data_polling(mock_modbus_client, mock_mqtt_publisher, state, sample_config)
        
        # Verify core sensor data was published
        mock_mqtt_publisher.publish_sensor_data.assert_called_once_with(mppt_data)
        
        # Verify diagnostic data publishing was not attempted (empty list is falsy)
        mock_mqtt_publisher.publish_diagnostic_data.assert_not_called()
        
        # Verify connection state remains healthy
        assert state.modbus_connected is True
        assert state.mqtt_connected is True

    def test_core_sensor_failure_triggers_modbus_reconnection(self, sample_config):
        """Test that core sensor failures trigger Modbus reconnection but don't affect diagnostic state."""
        # Create mocks
        mock_modbus_client = Mock()
        mock_mqtt_publisher = Mock()
        
        # Set up connection state
        state = ConnectionState()
        state.modbus_connected = True
        state.model_160_verified = True
        state.mqtt_connected = True
        state.diagnostic_discovery_published = True
        
        # Mock failed MPPT data read (core failure)
        mock_modbus_client.read_mppt_data.return_value = None
        
        # Call data polling
        handle_data_polling(mock_modbus_client, mock_mqtt_publisher, state, sample_config)
        
        # Verify Modbus connection is marked as failed
        assert state.modbus_connected is False
        assert state.model_160_verified is False
        
        # Verify MQTT connection remains intact
        assert state.mqtt_connected is True
        
        # Verify diagnostic discovery state is preserved (not reset by core failure)
        assert state.diagnostic_discovery_published is True
        
        # Verify no publishing was attempted
        mock_mqtt_publisher.publish_sensor_data.assert_not_called()
        mock_mqtt_publisher.publish_diagnostic_data.assert_not_called()

    def test_mqtt_connection_loss_resets_diagnostic_discovery_flag(self, sample_config):
        """Test that MQTT connection loss resets diagnostic discovery flag."""
        # Create mocks
        mock_modbus_client = Mock()
        mock_mqtt_publisher = Mock()
        
        # Set up connection state
        state = ConnectionState()
        state.modbus_connected = True
        state.model_160_verified = True
        state.mqtt_connected = True
        state.diagnostic_discovery_published = True  # Previously published
        
        # Create sample MPPT data
        mppt_data = MPPTData(
            mppt1=MPPTChannelData(voltage=400.5, current=10.2, power=4085.1),
            mppt2=MPPTChannelData(voltage=395.3, current=9.8, power=3873.94),
            total_power=7959.04,
            timestamp=Mock(),
            modules=[]
        )
        
        # Mock successful MPPT data read
        mock_modbus_client.read_mppt_data.return_value = mppt_data
        
        # Mock core sensor publishing failure due to MQTT disconnection
        mock_mqtt_publisher.publish_sensor_data.return_value = False
        mock_mqtt_publisher.is_connected.return_value = False  # MQTT disconnected
        
        # Call data polling
        handle_data_polling(mock_modbus_client, mock_mqtt_publisher, state, sample_config)
        
        # Verify MQTT connection is marked as failed
        assert state.mqtt_connected is False
        
        # Verify diagnostic discovery flag is reset
        assert state.diagnostic_discovery_published is False
        
        # Verify Modbus connection remains intact
        assert state.modbus_connected is True
        assert state.model_160_verified is True