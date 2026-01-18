"""
Tests for error handling scenarios in core components.
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from fronius_modbus.config import Config, ConfigValidationError
from fronius_modbus.modbus_client import ModbusClient
from fronius_modbus.mqtt_publisher import MQTTPublisher


class TestErrorHandling:
    """Test error handling in core components."""

    def test_config_invalid_yaml(self):
        """Test that Config handles invalid YAML gracefully."""
        invalid_yaml = """
modbus:
  host: "test"
  port: invalid_port  # This should be an integer
  unit_id: 1
  timeout: 10
mqtt:
  broker: "test"
  port: 1883
  username: "test"
  password: "test"
  client_id: "test"
  topic_prefix: "homeassistant"
application:
  poll_interval: 5
  log_level: "INFO"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(invalid_yaml)
            f.flush()

            try:
                with pytest.raises(ConfigValidationError):
                    Config(f.name)
            finally:
                os.unlink(f.name)

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_modbus_connection_failure(self, mock_sunspec):
        """Test that ModbusClient handles connection failures gracefully."""
        # Mock the pysunspec2 client to raise an exception
        mock_sunspec.side_effect = Exception("Connection failed")

        client = ModbusClient("192.168.1.100", 502, 1, 10)

        # Connection should fail gracefully
        result = client.connect()
        assert result is False
        assert not client.is_connected()

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_modbus_model_160_not_found(self, mock_sunspec):
        """Test that ModbusClient handles missing Model 160 gracefully."""
        # Mock the pysunspec2 client
        mock_device = Mock()
        mock_device.models = {1: [Mock()]}  # Only Model 1, no Model 160
        mock_sunspec.return_value = mock_device

        client = ModbusClient("192.168.1.100", 502, 1, 10)

        # Connect should succeed
        result = client.connect()
        assert result is True

        # But Model 160 verification should fail
        result = client.verify_model_160()
        assert result is False

    @patch("paho.mqtt.client.Client")
    def test_mqtt_connection_failure(self, mock_mqtt_client):
        """Test that MQTTPublisher handles connection failures gracefully."""
        # Mock the paho-mqtt client to fail connection
        mock_client = Mock()
        mock_client.connect.side_effect = Exception("Connection failed")
        mock_mqtt_client.return_value = mock_client

        publisher = MQTTPublisher(
            broker="192.168.1.50",
            port=1883,
            username="test",
            password="test",
            client_id="test_client",
            topic_prefix="homeassistant",
        )

        # Connection should fail gracefully
        result = publisher.connect()
        assert result is False
        assert not publisher.is_connected()

    @patch("paho.mqtt.client.Client")
    def test_mqtt_publish_when_not_connected(self, mock_mqtt_client):
        """Test that MQTTPublisher handles publishing when not connected."""
        mock_client = Mock()
        mock_mqtt_client.return_value = mock_client

        publisher = MQTTPublisher(
            broker="192.168.1.50",
            port=1883,
            username="test",
            password="test",
            client_id="test_client",
            topic_prefix="homeassistant",
        )

        # Try to publish discovery without being connected
        device_info = {"manufacturer": "Fronius", "model": "Symo", "serial_number": "12345"}

        result = publisher.publish_discovery(device_info)
        assert result is False

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_modbus_read_data_when_not_connected(self, mock_sunspec):
        """Test that ModbusClient handles data reading when not connected."""
        client = ModbusClient("192.168.1.100", 502, 1, 10)

        # Try to read data without connecting
        result = client.read_mppt_data()
        assert result is None

        result = client.read_device_info()
        assert result is None

        result = client.verify_model_160()
        assert result is False
