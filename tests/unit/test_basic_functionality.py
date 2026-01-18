"""
Basic functionality tests to verify core components can be instantiated and work together.
"""

import os
import tempfile
from unittest.mock import Mock, patch

from fronius_modbus.config import Config
from fronius_modbus.controller import FroniusBridgeController
from fronius_modbus.modbus_client import ModbusClient
from fronius_modbus.mqtt_publisher import MQTTPublisher


class TestBasicFunctionality:
    """Test basic functionality of core components."""

    def test_config_instantiation(self):
        """Test that Config can be instantiated with valid configuration."""
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
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            try:
                config = Config(f.name)
                assert config.modbus_host == "192.168.1.100"
                assert config.modbus_port == 502
                assert config.mqtt_broker == "192.168.1.50"
                assert config.poll_interval == 5
            finally:
                os.unlink(f.name)

    def test_modbus_client_instantiation(self):
        """Test that ModbusClient can be instantiated."""
        client = ModbusClient("192.168.1.100", 502, 1, 10)
        assert client._host == "192.168.1.100"
        assert client._port == 502
        assert client._unit_id == 1
        assert client._timeout == 10
        assert not client.is_connected()

    def test_mqtt_publisher_instantiation(self):
        """Test that MQTTPublisher can be instantiated."""
        publisher = MQTTPublisher(
            broker="192.168.1.50",
            port=1883,
            username="test",
            password="test",
            client_id="test_client",
            topic_prefix="homeassistant",
        )
        assert publisher._broker == "192.168.1.50"
        assert publisher._port == 1883
        assert not publisher.is_connected()

    def test_controller_instantiation(self):
        """Test that FroniusBridgeController can be instantiated with valid config."""
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
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            try:
                config = Config(f.name)
                controller = FroniusBridgeController(config)
                assert controller.config == config
                assert controller.modbus_client is not None
                assert controller.mqtt_publisher is not None
            finally:
                os.unlink(f.name)

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_modbus_client_connection_attempt(self, mock_sunspec):
        """Test that ModbusClient attempts connection properly."""
        # Mock the pysunspec2 client
        mock_device = Mock()
        mock_sunspec.return_value = mock_device

        client = ModbusClient("192.168.1.100", 502, 1, 10)

        # Test successful connection
        mock_device.scan.return_value = None
        client.connect()

        # Verify the client was created with correct parameters
        mock_sunspec.assert_called_once_with(
            slave_id=1, ipaddr="192.168.1.100", ipport=502, timeout=10
        )

        # Verify scan was called
        mock_device.scan.assert_called_once()

    @patch("paho.mqtt.client.Client")
    def test_mqtt_publisher_connection_attempt(self, mock_mqtt_client):
        """Test that MQTTPublisher attempts connection properly."""
        # Mock the paho-mqtt client
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

        # Test connection attempt
        mock_client.connect.return_value = 0  # Success
        
        # Mock the connection callback to simulate successful connection
        def mock_connect_side_effect(*args, **kwargs):
            # Simulate the _on_connect callback being called
            publisher._connected = True
            return 0
        
        mock_client.connect.side_effect = mock_connect_side_effect
        
        result = publisher.connect()

        # Verify the client was configured properly
        mock_client.username_pw_set.assert_called_once_with("test", "test")
        mock_client.connect.assert_called_once_with("192.168.1.50", 1883, keepalive=60)
        mock_client.loop_start.assert_called_once()
        
        # Verify connection was successful
        assert result is True
        assert publisher.is_connected() is True
