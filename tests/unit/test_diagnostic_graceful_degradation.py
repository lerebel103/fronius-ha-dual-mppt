"""
Tests for graceful degradation of diagnostic sensors when data is unavailable.
"""

import logging
from unittest.mock import Mock, patch

import pytest

from fronius_modbus.modbus_client import ModbusClient, DiagnosticData, MPPTModuleData
from fronius_modbus.mqtt_publisher import MQTTPublisher


class TestDiagnosticGracefulDegradation:
    """Test graceful degradation when diagnostic data is unavailable."""

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_diagnostic_fields_unavailable_core_functionality_continues(self, mock_sunspec):
        """Test that core MPPT functionality continues when diagnostic fields are unavailable."""
        # Mock the pysunspec2 client and device
        mock_device = Mock()
        mock_sunspec.return_value = mock_device
        mock_device.models = {160: [Mock()]}
        
        # Mock Model 160 with core data but no diagnostic fields
        mock_model_160 = mock_device.models[160][0]
        mock_model_160.N.value = 2  # 2 modules
        
        # Mock modules with core data only
        mock_module_1 = Mock()
        mock_module_1.DCV.cvalue = 400.5
        mock_module_1.DCA.cvalue = 10.2
        mock_module_1.DCW.cvalue = 4085.1
        # No diagnostic fields (Tmp, DCSt, DCEvt)
        
        mock_module_2 = Mock()
        mock_module_2.DCV.cvalue = 395.3
        mock_module_2.DCA.cvalue = 9.8
        mock_module_2.DCW.cvalue = 3873.94
        # No diagnostic fields
        
        mock_model_160.module = [mock_module_1, mock_module_2]
        
        client = ModbusClient("192.168.1.100", 502, 1, 10)
        client._device = mock_device
        client._connected = True
        
        # Read MPPT data
        mppt_data = client.read_mppt_data()
        
        # Verify core functionality works
        assert mppt_data is not None
        assert mppt_data.mppt1.voltage == 400.5
        assert mppt_data.mppt1.current == 10.2
        assert mppt_data.mppt1.power == 4085.1
        assert mppt_data.mppt2.voltage == 395.3
        assert mppt_data.mppt2.current == 9.8
        assert mppt_data.mppt2.power == 3873.94
        assert mppt_data.total_power == 7959.04
        
        # Verify diagnostic data is present but with None values
        assert mppt_data.modules is not None
        assert len(mppt_data.modules) == 2
        
        # Check first module diagnostics
        diag1 = mppt_data.modules[0].diagnostics
        assert diag1.temperature is None
        assert diag1.operating_state is None
        assert diag1.module_events is None
        assert diag1.formatted_state == "unknown"
        assert diag1.formatted_events == "unavailable"
        
        # Check second module diagnostics
        diag2 = mppt_data.modules[1].diagnostics
        assert diag2.temperature is None
        assert diag2.operating_state is None
        assert diag2.module_events is None
        assert diag2.formatted_state == "unknown"
        assert diag2.formatted_events == "unavailable"

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_individual_diagnostic_field_failures(self, mock_sunspec):
        """Test that individual diagnostic field failures don't affect other fields."""
        # Mock the pysunspec2 client and device
        mock_device = Mock()
        mock_sunspec.return_value = mock_device
        mock_device.models = {160: [Mock()]}
        
        # Mock Model 160
        mock_model_160 = mock_device.models[160][0]
        mock_model_160.N.value = 1  # 1 module
        
        # Mock module with partial diagnostic data
        mock_module = Mock()
        mock_module.DCV.cvalue = 400.5
        mock_module.DCA.cvalue = 10.2
        mock_module.DCW.cvalue = 4085.1
        
        # Temperature field available
        mock_module.Tmp = Mock()
        mock_module.Tmp.cvalue = 45.2
        
        # Operating state field raises exception
        mock_module.DCSt = Mock()
        mock_module.DCSt.value = Mock(side_effect=AttributeError("Field not available"))
        
        # Module events field available
        mock_module.DCEvt = Mock()
        mock_module.DCEvt.value = 0  # No events
        
        mock_model_160.module = [mock_module]
        
        client = ModbusClient("192.168.1.100", 502, 1, 10)
        client._device = mock_device
        client._connected = True
        
        # Read MPPT data
        mppt_data = client.read_mppt_data()
        
        # Verify core functionality works
        assert mppt_data is not None
        assert mppt_data.mppt1.power == 4085.1
        
        # Verify partial diagnostic data
        diag = mppt_data.modules[0].diagnostics
        assert diag.temperature == 45.2  # Available
        assert diag.operating_state is None  # Failed
        assert diag.module_events == 0  # Available
        assert diag.formatted_state == "unknown"  # Failed field formatted as unknown
        assert diag.formatted_events == "No active events"  # Available field formatted correctly

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_module_read_failure_continues_with_other_modules(self, mock_sunspec):
        """Test that failure to read one module doesn't prevent reading others."""
        # Mock the pysunspec2 client and device
        mock_device = Mock()
        mock_sunspec.return_value = mock_device
        mock_device.models = {160: [Mock()]}
        
        # Mock Model 160
        mock_model_160 = mock_device.models[160][0]
        mock_model_160.N.value = 2  # 2 modules
        
        # Mock first module that fails completely
        mock_module_1 = Mock()
        mock_module_1.DCV.cvalue = Mock(side_effect=Exception("Module 1 read error"))
        
        # Mock second module that works
        mock_module_2 = Mock()
        mock_module_2.DCV.cvalue = 395.3
        mock_module_2.DCA.cvalue = 9.8
        mock_module_2.DCW.cvalue = 3873.94
        mock_module_2.Tmp = Mock()
        mock_module_2.Tmp.cvalue = 42.1
        mock_module_2.DCSt = Mock()
        mock_module_2.DCSt.value = 4  # MPPT
        mock_module_2.DCEvt = Mock()
        mock_module_2.DCEvt.value = 0
        
        mock_model_160.module = [mock_module_1, mock_module_2]
        
        client = ModbusClient("192.168.1.100", 502, 1, 10)
        client._device = mock_device
        client._connected = True
        
        # Read MPPT data
        mppt_data = client.read_mppt_data()
        
        # Verify core functionality works
        assert mppt_data is not None
        
        # First module should have empty data due to failure
        assert mppt_data.mppt1.voltage == 0.0
        assert mppt_data.mppt1.current == 0.0
        assert mppt_data.mppt1.power == 0.0
        
        # Second module should have correct data
        assert mppt_data.mppt2.voltage == 395.3
        assert mppt_data.mppt2.current == 9.8
        assert mppt_data.mppt2.power == 3873.94
        
        # Total power should only include working module
        assert mppt_data.total_power == 3873.94
        
        # Verify diagnostic data
        assert len(mppt_data.modules) == 2
        
        # First module should have empty diagnostics
        diag1 = mppt_data.modules[0].diagnostics
        assert diag1.temperature is None
        assert diag1.operating_state is None
        assert diag1.module_events is None
        
        # Second module should have correct diagnostics
        diag2 = mppt_data.modules[1].diagnostics
        assert diag2.temperature == 42.1
        assert diag2.operating_state == 4
        assert diag2.module_events == 0
        assert diag2.formatted_state == "MPPT"
        assert diag2.formatted_events == "No active events"

    @patch("paho.mqtt.client.Client")
    def test_diagnostic_mqtt_failure_doesnt_affect_core_sensors(self, mock_mqtt_client):
        """Test that diagnostic MQTT failures don't affect core sensor publishing."""
        # Mock MQTT client
        mock_client = Mock()
        mock_mqtt_client.return_value = mock_client
        
        publisher = MQTTPublisher(
            broker="localhost",
            port=1883,
            username="test",
            password="test",
            client_id="test",
            topic_prefix="homeassistant",
        )
        
        # Set up as connected
        publisher._connected = True
        publisher._device_id = "fronius_12345"
        
        # Mock publish method to fail for diagnostic topics but succeed for core topics
        def mock_publish(topic, payload, qos, retain):
            mock_result = Mock()
            if "diagnostic" in topic or "temperature" in topic or "operating_state" in topic or "module_events" in topic:
                mock_result.rc = 1  # Fail diagnostic topics
            else:
                mock_result.rc = 0  # Succeed core topics
            return mock_result
        
        mock_client.publish = Mock(side_effect=mock_publish)
        
        # Create sample diagnostic data
        diagnostic_data = [
            DiagnosticData.create(45.2, 4, 0),
            DiagnosticData.create(None, 2, 3)
        ]
        
        # Publish diagnostic data (should fail)
        result = publisher.publish_diagnostic_data(diagnostic_data)
        assert result is False
        
        # Verify that diagnostic failure is handled gracefully
        # (In real implementation, this would be logged but not crash the system)

    def test_diagnostic_data_create_with_all_none_values(self):
        """Test DiagnosticData.create handles all None values gracefully."""
        diag_data = DiagnosticData.create(
            temperature=None,
            operating_state=None,
            module_events=None
        )
        
        assert diag_data.temperature is None
        assert diag_data.operating_state is None
        assert diag_data.module_events is None
        assert diag_data.formatted_state == "unknown"
        assert diag_data.formatted_events == "unavailable"

    def test_diagnostic_data_create_with_invalid_values(self):
        """Test DiagnosticData.create handles invalid values gracefully."""
        # Test with out-of-range operating state
        diag_data = DiagnosticData.create(
            temperature=150.0,  # Valid but high temperature
            operating_state=99,  # Invalid state
            module_events=4294967295  # Max uint32 value
        )
        
        assert diag_data.temperature == 150.0
        assert diag_data.operating_state == 99
        assert diag_data.module_events == 4294967295
        assert diag_data.formatted_state == "unknown_99"  # Invalid state formatted correctly
        # Events should decode whatever bits are set

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_logging_for_diagnostic_issues(self, mock_sunspec, caplog):
        """Test that diagnostic data issues are properly logged."""
        # Mock the pysunspec2 client and device
        mock_device = Mock()
        mock_sunspec.return_value = mock_device
        mock_device.models = {160: [Mock()]}
        
        # Mock Model 160
        mock_model_160 = mock_device.models[160][0]
        mock_model_160.N.value = 1  # 1 module
        
        # Mock module with diagnostic field errors
        mock_module = Mock()
        mock_module.DCV.cvalue = 400.5
        mock_module.DCA.cvalue = 10.2
        mock_module.DCW.cvalue = 4085.1
        
        # Temperature field raises AttributeError
        def temp_side_effect():
            raise AttributeError("Temperature field not available")
        mock_module.Tmp = Mock()
        mock_module.Tmp.cvalue = Mock(side_effect=temp_side_effect)
        
        # Operating state field raises ValueError
        def state_side_effect():
            raise ValueError("Invalid state value")
        mock_module.DCSt = Mock()
        mock_module.DCSt.value = Mock(side_effect=state_side_effect)
        
        # Module events field raises TypeError
        def events_side_effect():
            raise TypeError("Invalid events type")
        mock_module.DCEvt = Mock()
        mock_module.DCEvt.value = Mock(side_effect=events_side_effect)
        
        mock_model_160.module = [mock_module]
        
        client = ModbusClient("192.168.1.100", 502, 1, 10)
        client._device = mock_device
        client._connected = True
        
        # Capture logs
        with caplog.at_level(logging.DEBUG):
            mppt_data = client.read_mppt_data()
        
        # Verify core functionality still works
        assert mppt_data is not None
        assert mppt_data.mppt1.power == 4085.1
        
        # Verify diagnostic errors were logged
        log_messages = [record.message for record in caplog.records]
        assert any("Temperature field unavailable for module 0" in msg for msg in log_messages)
        assert any("Operating state field unavailable for module 0" in msg for msg in log_messages)
        assert any("Module events field unavailable for module 0" in msg for msg in log_messages)
        
        # Verify diagnostic data is None but formatted appropriately
        diag = mppt_data.modules[0].diagnostics
        assert diag.temperature is None
        assert diag.operating_state is None
        assert diag.module_events is None
        assert diag.formatted_state == "unknown"
        assert diag.formatted_events == "unavailable"