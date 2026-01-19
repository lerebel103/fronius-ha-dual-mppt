"""Unit tests for MQTT publisher."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from fronius_modbus.modbus_client import MPPTChannelData, MPPTData, DiagnosticData
from fronius_modbus.mqtt_publisher import MQTTPublisher


@pytest.fixture
def mqtt_publisher():
    """Create an MQTTPublisher instance for testing."""
    return MQTTPublisher(
        broker="localhost",
        port=1883,
        username="test_user",
        password="test_pass",
        client_id="test_client",
        topic_prefix="homeassistant",
    )


@pytest.fixture
def sample_mppt_data():
    """Create sample MPPT data for testing."""
    return MPPTData(
        mppt1=MPPTChannelData(voltage=400.5, current=10.2, power=4085.1),
        mppt2=MPPTChannelData(voltage=395.3, current=9.8, power=3873.94),
        total_power=7959.04,
        timestamp=datetime(2024, 1, 15, 12, 30, 45),
    )


@pytest.fixture
def device_info():
    """Create sample device info for testing."""
    return {
        "manufacturer": "Fronius",
        "model": "Symo 10.0-3-M",
        "serial_number": "12345678",
    }


@pytest.fixture
def sample_diagnostic_data():
    """Create sample diagnostic data for testing."""
    return [
        DiagnosticData.create(
            temperature=45.2,
            operating_state=4,  # MPPT
            module_events=0  # No events
        ),
        DiagnosticData.create(
            temperature=None,  # Unavailable
            operating_state=2,  # SLEEPING
            module_events=3  # GROUND_FAULT (bit 0) + INPUT_OVER_VOLTAGE (bit 1)
        )
    ]


class TestMQTTPublisher:
    """Test cases for MQTTPublisher class."""

    def test_init(self, mqtt_publisher):
        """Test MQTTPublisher initialization."""
        assert mqtt_publisher._broker == "localhost"
        assert mqtt_publisher._port == 1883
        assert mqtt_publisher._username == "test_user"
        assert mqtt_publisher._password == "test_pass"
        assert mqtt_publisher._client_id == "test_client"
        assert mqtt_publisher._topic_prefix == "homeassistant"
        assert mqtt_publisher._connected is False
        assert mqtt_publisher._device_id is None

    def test_publish_sensor_data_not_connected(self, mqtt_publisher, sample_mppt_data):
        """Test publish_sensor_data when not connected."""
        result = mqtt_publisher.publish_sensor_data(sample_mppt_data)
        assert result is False

    def test_publish_sensor_data_no_device_id(self, mqtt_publisher, sample_mppt_data):
        """Test publish_sensor_data when device_id is not set."""
        mqtt_publisher._connected = True
        result = mqtt_publisher.publish_sensor_data(sample_mppt_data)
        assert result is False

    @patch("paho.mqtt.client.Client")
    def test_publish_sensor_data_success(
        self, mock_mqtt_client, mqtt_publisher, sample_mppt_data, device_info
    ):
        """Test successful publish_sensor_data."""
        # Set up the publisher as connected with device_id
        mqtt_publisher._connected = True
        mqtt_publisher._device_id = "fronius_12345678"

        # Mock the publish method to return success
        mock_result = MagicMock()
        mock_result.rc = 0  # MQTT_ERR_SUCCESS
        mqtt_publisher._client.publish = MagicMock(return_value=mock_result)

        # Call publish_sensor_data
        result = mqtt_publisher.publish_sensor_data(sample_mppt_data)

        # Verify success
        assert result is True

        # Verify publish was called 7 times (3 for PV1, 3 for PV2, 1 for total)
        assert mqtt_publisher._client.publish.call_count == 7

        # Verify the calls were made with correct topics and payloads
        calls = mqtt_publisher._client.publish.call_args_list

        # Check PV1 voltage
        args, kwargs = calls[0]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/pv1_voltage/state"
        payload_dict = json.loads(payload)
        assert payload_dict["voltage"] == 400.5
        assert payload_dict["timestamp"] == "2024-01-15T12:30:45"

        # Check PV1 current
        args, kwargs = calls[1]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/pv1_current/state"
        payload_dict = json.loads(payload)
        assert payload_dict["current"] == 10.2
        assert payload_dict["timestamp"] == "2024-01-15T12:30:45"

        # Check PV1 power
        args, kwargs = calls[2]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/pv1_power/state"
        payload_dict = json.loads(payload)
        assert payload_dict["power"] == 4085.1
        assert payload_dict["timestamp"] == "2024-01-15T12:30:45"

        # Check PV2 voltage
        args, kwargs = calls[3]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/pv2_voltage/state"
        payload_dict = json.loads(payload)
        assert payload_dict["voltage"] == 395.3
        assert payload_dict["timestamp"] == "2024-01-15T12:30:45"

        # Check PV2 current
        args, kwargs = calls[4]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/pv2_current/state"
        payload_dict = json.loads(payload)
        assert payload_dict["current"] == 9.8
        assert payload_dict["timestamp"] == "2024-01-15T12:30:45"

        # Check PV2 power
        args, kwargs = calls[5]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/pv2_power/state"
        payload_dict = json.loads(payload)
        assert payload_dict["power"] == 3873.94
        assert payload_dict["timestamp"] == "2024-01-15T12:30:45"

        # Check total power
        args, kwargs = calls[6]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/total_power/state"
        payload_dict = json.loads(payload)
        assert payload_dict["power"] == 7959.04
        assert payload_dict["timestamp"] == "2024-01-15T12:30:45"

    @patch("paho.mqtt.client.Client")
    def test_publish_sensor_data_publish_failure(
        self, mock_mqtt_client, mqtt_publisher, sample_mppt_data
    ):
        """Test publish_sensor_data when publish fails."""
        # Set up the publisher as connected with device_id
        mqtt_publisher._connected = True
        mqtt_publisher._device_id = "fronius_12345678"

        # Mock the publish method to return failure
        mock_result = MagicMock()
        mock_result.rc = 1  # MQTT error code
        mqtt_publisher._client.publish = MagicMock(return_value=mock_result)

        # Call publish_sensor_data
        result = mqtt_publisher.publish_sensor_data(sample_mppt_data)

        # Verify failure
        assert result is False

    def test_publish_sensor_data_json_format(self, mqtt_publisher, sample_mppt_data):
        """Test that publish_sensor_data creates valid JSON payloads."""
        # Set up the publisher as connected with device_id
        mqtt_publisher._connected = True
        mqtt_publisher._device_id = "fronius_12345678"

        # Mock the publish method to capture payloads
        published_payloads = []

        def capture_publish(topic, payload, qos, retain):
            published_payloads.append(payload)
            mock_result = MagicMock()
            mock_result.rc = 0
            return mock_result

        mqtt_publisher._client.publish = MagicMock(side_effect=capture_publish)

        # Call publish_sensor_data
        result = mqtt_publisher.publish_sensor_data(sample_mppt_data)

        # Verify success
        assert result is True

        # Verify all payloads are valid JSON
        for payload in published_payloads:
            payload_dict = json.loads(payload)
            assert "timestamp" in payload_dict
            assert payload_dict["timestamp"] == "2024-01-15T12:30:45"

            # Check that at least one metric is present
            assert any(key in payload_dict for key in ["voltage", "current", "power"])

    def test_publish_sensor_data_numeric_values(self, mqtt_publisher, sample_mppt_data):
        """Test that publish_sensor_data includes numeric values."""
        # Set up the publisher as connected with device_id
        mqtt_publisher._connected = True
        mqtt_publisher._device_id = "fronius_12345678"

        # Mock the publish method to capture payloads
        published_payloads = []

        def capture_publish(topic, payload, qos, retain):
            published_payloads.append(payload)
            mock_result = MagicMock()
            mock_result.rc = 0
            return mock_result

        mqtt_publisher._client.publish = MagicMock(side_effect=capture_publish)

        # Call publish_sensor_data
        result = mqtt_publisher.publish_sensor_data(sample_mppt_data)

        # Verify success
        assert result is True

        # Verify all numeric values can be parsed as floats
        for payload in published_payloads:
            payload_dict = json.loads(payload)

            # Check voltage, current, or power values
            if "voltage" in payload_dict:
                assert isinstance(payload_dict["voltage"], (int, float))
                assert payload_dict["voltage"] >= 0

            if "current" in payload_dict:
                assert isinstance(payload_dict["current"], (int, float))
                assert payload_dict["current"] >= 0

            if "power" in payload_dict:
                assert isinstance(payload_dict["power"], (int, float))
                assert payload_dict["power"] >= 0

    @patch("paho.mqtt.client.Client")
    def test_publish_discovery_includes_expire_after(
        self, mock_mqtt_client, mqtt_publisher, device_info
    ):
        """Test that publish_discovery includes expire_after parameter."""
        # Set up the publisher as connected
        mqtt_publisher._connected = True

        # Mock the publish method to capture payloads
        published_payloads = []

        def capture_publish(topic, payload, qos, retain):
            published_payloads.append((topic, payload))
            mock_result = MagicMock()
            mock_result.rc = 0
            return mock_result

        mqtt_publisher._client.publish = MagicMock(side_effect=capture_publish)

        # Call publish_discovery
        result = mqtt_publisher.publish_discovery(device_info)

        # Verify success
        assert result is True

        # Verify all discovery messages include expire_after
        for topic, payload in published_payloads:
            if "/config" in topic:  # Discovery message
                payload_dict = json.loads(payload)
                assert "expire_after" in payload_dict
                assert payload_dict["expire_after"] == 3600

    def test_publish_diagnostic_discovery_not_connected(self, mqtt_publisher, device_info):
        """Test publish_diagnostic_discovery when not connected."""
        result = mqtt_publisher.publish_diagnostic_discovery(device_info, num_modules=2)
        assert result is False

    @patch("paho.mqtt.client.Client")
    def test_publish_diagnostic_discovery_success(self, mock_mqtt_client, mqtt_publisher, device_info):
        """Test successful publish_diagnostic_discovery."""
        # Set up the publisher as connected
        mqtt_publisher._connected = True

        # Mock the publish method to return success
        mock_result = MagicMock()
        mock_result.rc = 0  # MQTT_ERR_SUCCESS
        mqtt_publisher._client.publish = MagicMock(return_value=mock_result)

        # Call publish_diagnostic_discovery for 2 modules with all sensors enabled
        result = mqtt_publisher.publish_diagnostic_discovery(
            device_info=device_info,
            num_modules=2,
            temperature_enabled=True,
            temperature_default=False,
            operating_state_enabled=True,
            operating_state_default=True,
            module_events_enabled=True,
            module_events_default=False
        )

        # Verify success
        assert result is True

        # Verify publish was called 6 times (3 sensor types × 2 modules)
        assert mqtt_publisher._client.publish.call_count == 6

        # Verify the calls were made with correct topics and payloads
        calls = mqtt_publisher._client.publish.call_args_list

        # Check temperature sensor for module 1
        args, kwargs = calls[0]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/mppt1_temperature/config"
        payload_dict = json.loads(payload)
        assert payload_dict["name"] == "MPPT1 Temperature"
        assert payload_dict["device_class"] == "temperature"
        assert payload_dict["unit_of_measurement"] == "°C"
        assert payload_dict["entity_category"] == "diagnostic"
        assert payload_dict["enabled_by_default"] is False

        # Check operating state sensor for module 1
        args, kwargs = calls[1]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/mppt1_operating_state/config"
        payload_dict = json.loads(payload)
        assert payload_dict["name"] == "MPPT1 Operating State"
        assert payload_dict["device_class"] == "enum"
        assert payload_dict["entity_category"] == "diagnostic"
        assert payload_dict["enabled_by_default"] is True

        # Check module events sensor for module 1
        args, kwargs = calls[2]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/mppt1_module_events/config"
        payload_dict = json.loads(payload)
        assert payload_dict["name"] == "MPPT1 Module Events"
        assert payload_dict["entity_category"] == "diagnostic"
        assert payload_dict["enabled_by_default"] is False
        assert "device_class" not in payload_dict  # Module events don't have device class

    @patch("paho.mqtt.client.Client")
    def test_publish_diagnostic_discovery_selective_sensors(self, mock_mqtt_client, mqtt_publisher, device_info):
        """Test publish_diagnostic_discovery with selective sensor types."""
        # Set up the publisher as connected
        mqtt_publisher._connected = True

        # Mock the publish method to return success
        mock_result = MagicMock()
        mock_result.rc = 0  # MQTT_ERR_SUCCESS
        mqtt_publisher._client.publish = MagicMock(return_value=mock_result)

        # Call publish_diagnostic_discovery with only temperature sensors enabled
        result = mqtt_publisher.publish_diagnostic_discovery(
            device_info=device_info,
            num_modules=1,
            temperature_enabled=True,
            temperature_default=True,
            operating_state_enabled=False,
            operating_state_default=False,
            module_events_enabled=False,
            module_events_default=False
        )

        # Verify success
        assert result is True

        # Verify publish was called only once (1 sensor type × 1 module)
        assert mqtt_publisher._client.publish.call_count == 1

        # Verify only temperature sensor was published
        args, kwargs = mqtt_publisher._client.publish.call_args_list[0]
        topic, payload = args[0], args[1]
        assert "temperature" in topic
        payload_dict = json.loads(payload)
        assert payload_dict["enabled_by_default"] is True

    def test_publish_diagnostic_data_not_connected(self, mqtt_publisher, sample_diagnostic_data):
        """Test publish_diagnostic_data when not connected."""
        result = mqtt_publisher.publish_diagnostic_data(sample_diagnostic_data)
        assert result is False

    def test_publish_diagnostic_data_no_device_id(self, mqtt_publisher, sample_diagnostic_data):
        """Test publish_diagnostic_data when device_id is not set."""
        mqtt_publisher._connected = True
        result = mqtt_publisher.publish_diagnostic_data(sample_diagnostic_data)
        assert result is False

    @patch("paho.mqtt.client.Client")
    def test_publish_diagnostic_data_success(self, mock_mqtt_client, mqtt_publisher, sample_diagnostic_data):
        """Test successful publish_diagnostic_data."""
        # Set up the publisher as connected with device_id
        mqtt_publisher._connected = True
        mqtt_publisher._device_id = "fronius_12345678"

        # Mock the publish method to return success
        mock_result = MagicMock()
        mock_result.rc = 0  # MQTT_ERR_SUCCESS
        mqtt_publisher._client.publish = MagicMock(return_value=mock_result)

        # Call publish_diagnostic_data
        result = mqtt_publisher.publish_diagnostic_data(sample_diagnostic_data)

        # Verify success
        assert result is True

        # Verify publish was called 6 times (3 sensor types × 2 modules)
        assert mqtt_publisher._client.publish.call_count == 6

        # Verify the calls were made with correct topics and payloads
        calls = mqtt_publisher._client.publish.call_args_list

        # Check temperature data for module 1 (available)
        args, kwargs = calls[0]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/mppt1_temperature/state"
        payload_dict = json.loads(payload)
        assert payload_dict["temperature"] == 45.2
        assert "timestamp" in payload_dict

        # Check operating state data for module 1
        args, kwargs = calls[1]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/mppt1_operating_state/state"
        payload_dict = json.loads(payload)
        assert payload_dict["state"] == "MPPT"
        assert "timestamp" in payload_dict

        # Check module events data for module 1
        args, kwargs = calls[2]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/mppt1_module_events/state"
        payload_dict = json.loads(payload)
        assert payload_dict["events"] == "No active events"
        assert "timestamp" in payload_dict

        # Check temperature data for module 2 (unavailable)
        args, kwargs = calls[3]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/mppt2_temperature/state"
        assert payload == "unavailable"

        # Check operating state data for module 2
        args, kwargs = calls[4]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/mppt2_operating_state/state"
        payload_dict = json.loads(payload)
        assert payload_dict["state"] == "SLEEPING"

        # Check module events data for module 2
        args, kwargs = calls[5]
        topic, payload = args[0], args[1]
        assert topic == "homeassistant/sensor/fronius_12345678/mppt2_module_events/state"
        payload_dict = json.loads(payload)
        assert "GROUND_FAULT" in payload_dict["events"]
        assert "INPUT_OVER_VOLTAGE" in payload_dict["events"]
    @patch("paho.mqtt.client.Client")
    def test_publish_diagnostic_discovery_resilient_sensor_creation(self, mock_mqtt_client, mqtt_publisher, device_info):
        """Test resilient sensor creation - continue with remaining sensors when individual sensors fail."""
        # Set up the publisher as connected
        mqtt_publisher._connected = True
        mqtt_publisher._device_id = "fronius_12345678"

        # Mock MQTT client with mixed success/failure results
        mock_result_success = MagicMock()
        mock_result_success.rc = 0  # MQTT_ERR_SUCCESS
        
        mock_result_failure = MagicMock()
        mock_result_failure.rc = 1  # MQTT_ERR_NOMEM (example failure)

        # Set up publish to fail for temperature sensors but succeed for others
        def mock_publish_side_effect(topic, payload, qos=0, retain=False):
            if "temperature" in topic:
                return mock_result_failure  # Temperature sensors fail
            else:
                return mock_result_success  # Other sensors succeed

        mqtt_publisher._client.publish = MagicMock(side_effect=mock_publish_side_effect)

        # Call publish_diagnostic_discovery for 2 modules with all sensors enabled
        result = mqtt_publisher.publish_diagnostic_discovery(
            device_info=device_info,
            num_modules=2,
            temperature_enabled=True,
            temperature_default=False,
            operating_state_enabled=True,
            operating_state_default=True,
            module_events_enabled=True,
            module_events_default=False
        )

        # Should return True because some sensors succeeded (resilient behavior)
        assert result is True

        # Verify publish was called for all 6 sensors (3 types × 2 modules)
        assert mqtt_publisher._client.publish.call_count == 6

        # Verify the correct topics were attempted
        call_topics = [call[0][0] for call in mqtt_publisher._client.publish.call_args_list]
        
        # Should have attempted all sensor types
        assert any("temperature" in topic for topic in call_topics)
        assert any("operating_state" in topic for topic in call_topics)
        assert any("module_events" in topic for topic in call_topics)
        
        # Should have attempted both modules
        assert any("mppt1" in topic for topic in call_topics)
        assert any("mppt2" in topic for topic in call_topics)

    @patch("paho.mqtt.client.Client")
    def test_publish_diagnostic_discovery_all_sensors_fail(self, mock_mqtt_client, mqtt_publisher, device_info):
        """Test behavior when all sensor creation attempts fail."""
        # Set up the publisher as connected
        mqtt_publisher._connected = True
        mqtt_publisher._device_id = "fronius_12345678"

        # Mock MQTT client to always fail
        mock_result_failure = MagicMock()
        mock_result_failure.rc = 1  # MQTT_ERR_NOMEM

        mqtt_publisher._client.publish = MagicMock(return_value=mock_result_failure)

        # Call publish_diagnostic_discovery for 1 module
        result = mqtt_publisher.publish_diagnostic_discovery(
            device_info=device_info,
            num_modules=1,
            temperature_enabled=True,
            temperature_default=False,
            operating_state_enabled=True,
            operating_state_default=True,
            module_events_enabled=True,
            module_events_default=False
        )

        # Should return False when all sensors fail
        assert result is False

        # Verify publish was called for all 3 sensors
        assert mqtt_publisher._client.publish.call_count == 3

    @patch("paho.mqtt.client.Client")
    def test_publish_diagnostic_discovery_exception_handling(self, mock_mqtt_client, mqtt_publisher, device_info):
        """Test resilient sensor creation with exceptions during individual sensor creation."""
        # Set up the publisher as connected
        mqtt_publisher._connected = True
        mqtt_publisher._device_id = "fronius_12345678"

        # Mock MQTT client to raise exception for temperature sensors
        def mock_publish_side_effect(topic, payload, qos=0, retain=False):
            if "temperature" in topic:
                raise Exception("Simulated MQTT publish exception")
            else:
                mock_result = MagicMock()
                mock_result.rc = 0  # Success for other sensors
                return mock_result

        mqtt_publisher._client.publish = MagicMock(side_effect=mock_publish_side_effect)

        # Call publish_diagnostic_discovery for 1 module
        result = mqtt_publisher.publish_diagnostic_discovery(
            device_info=device_info,
            num_modules=1,
            temperature_enabled=True,
            temperature_default=False,
            operating_state_enabled=True,
            operating_state_default=True,
            module_events_enabled=True,
            module_events_default=False
        )

        # Should return True because some sensors succeeded despite exceptions
        assert result is True

        # Verify publish was called for all 3 sensors (exception doesn't prevent other attempts)
        assert mqtt_publisher._client.publish.call_count == 3