"""
Tests for ModbusClient MPPT data reading functionality.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from fronius_modbus.modbus_client import (
    ModbusClient, 
    MPPTChannelData, 
    MPPTData,
    MPPTModuleData,
    DiagnosticData,
    OperatingStateFormatter,
    ModuleEventsDecoder
)


class TestModbusClient:
    """Test ModbusClient MPPT data reading functionality."""

    @pytest.fixture
    def modbus_client(self):
        """Create a ModbusClient instance for testing."""
        return ModbusClient("192.168.1.100", 502, 1, 10)

    @pytest.fixture
    def mock_model_160_single_module(self):
        """Mock Model 160 with single MPPT module."""
        mock_model = Mock()
        mock_model.N.value = 1
        
        # Mock single module
        mock_module = Mock()
        mock_module.DCV.cvalue = 400.5
        mock_module.DCA.cvalue = 10.2
        mock_module.DCW.cvalue = 4085.1
        
        mock_model.module = [mock_module]
        return mock_model

    @pytest.fixture
    def mock_model_160_dual_module(self):
        """Mock Model 160 with dual MPPT modules."""
        mock_model = Mock()
        mock_model.N.value = 2
        
        # Mock first module
        mock_module1 = Mock()
        mock_module1.DCV.cvalue = 400.5
        mock_module1.DCA.cvalue = 10.2
        mock_module1.DCW.cvalue = 4085.1
        
        # Mock second module
        mock_module2 = Mock()
        mock_module2.DCV.cvalue = 395.3
        mock_module2.DCA.cvalue = 9.8
        mock_module2.DCW.cvalue = 3873.94
        
        mock_model.module = [mock_module1, mock_module2]
        return mock_model

    @pytest.fixture
    def mock_model_160_no_modules(self):
        """Mock Model 160 with no MPPT modules."""
        mock_model = Mock()
        mock_model.N.value = 0
        mock_model.module = []
        return mock_model

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_read_mppt_data_single_module(self, mock_sunspec, modbus_client, mock_model_160_single_module):
        """Test reading MPPT data with single module."""
        # Setup mock device
        mock_device = Mock()
        mock_device.models = {160: [mock_model_160_single_module]}
        mock_sunspec.return_value = mock_device
        modbus_client._device = mock_device
        modbus_client._connected = True

        # Read MPPT data
        result = modbus_client.read_mppt_data()

        # Verify result
        assert result is not None
        assert isinstance(result, MPPTData)
        
        # Check MPPT1 data (from first module)
        assert result.mppt1.voltage == 400.5
        assert result.mppt1.current == 10.2
        assert result.mppt1.power == 4085.1
        
        # Check MPPT2 data (should be empty since only one module)
        assert result.mppt2.voltage == 0.0
        assert result.mppt2.current == 0.0
        assert result.mppt2.power == 0.0
        
        # Check total power
        assert result.total_power == 4085.1
        
        # Verify model was read
        mock_model_160_single_module.read.assert_called_once()

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_read_mppt_data_dual_module(self, mock_sunspec, modbus_client, mock_model_160_dual_module):
        """Test reading MPPT data with dual modules."""
        # Setup mock device
        mock_device = Mock()
        mock_device.models = {160: [mock_model_160_dual_module]}
        mock_sunspec.return_value = mock_device
        modbus_client._device = mock_device
        modbus_client._connected = True

        # Read MPPT data
        result = modbus_client.read_mppt_data()

        # Verify result
        assert result is not None
        assert isinstance(result, MPPTData)
        
        # Check MPPT1 data (from first module)
        assert result.mppt1.voltage == 400.5
        assert result.mppt1.current == 10.2
        assert result.mppt1.power == 4085.1
        
        # Check MPPT2 data (from second module)
        assert result.mppt2.voltage == 395.3
        assert result.mppt2.current == 9.8
        assert result.mppt2.power == 3873.94
        
        # Check total power (sum of both modules)
        assert result.total_power == 4085.1 + 3873.94
        
        # Verify model was read
        mock_model_160_dual_module.read.assert_called_once()

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_read_mppt_data_no_modules(self, mock_sunspec, modbus_client, mock_model_160_no_modules):
        """Test reading MPPT data with no modules available."""
        # Setup mock device
        mock_device = Mock()
        mock_device.models = {160: [mock_model_160_no_modules]}
        mock_sunspec.return_value = mock_device
        modbus_client._device = mock_device
        modbus_client._connected = True

        # Read MPPT data
        result = modbus_client.read_mppt_data()

        # Should return None when no modules available
        assert result is None
        
        # Verify model was read
        mock_model_160_no_modules.read.assert_called_once()

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_read_mppt_data_module_read_error(self, mock_sunspec, modbus_client):
        """Test reading MPPT data when module read fails."""
        # Setup mock model with module that raises exception
        mock_model = Mock()
        mock_model.N.value = 1
        
        mock_module = Mock()
        mock_module.DCV.cvalue = None  # Simulate read error
        mock_module.DCA.cvalue = None
        mock_module.DCW.cvalue = None
        
        mock_model.module = [mock_module]
        
        # Setup mock device
        mock_device = Mock()
        mock_device.models = {160: [mock_model]}
        mock_sunspec.return_value = mock_device
        modbus_client._device = mock_device
        modbus_client._connected = True

        # Read MPPT data
        result = modbus_client.read_mppt_data()

        # Should still return data with zero values
        assert result is not None
        assert result.mppt1.voltage == 0.0
        assert result.mppt1.current == 0.0
        assert result.mppt1.power == 0.0
        assert result.total_power == 0.0

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_read_mppt_data_partial_module_failure(self, mock_sunspec, modbus_client):
        """Test reading MPPT data when one module fails but others succeed."""
        # Setup mock model with two modules, second one fails
        mock_model = Mock()
        mock_model.N.value = 2
        
        # First module works
        mock_module1 = Mock()
        mock_module1.DCV.cvalue = 400.5
        mock_module1.DCA.cvalue = 10.2
        mock_module1.DCW.cvalue = 4085.1
        
        # Second module fails
        mock_module2 = Mock()
        mock_module2.DCV.cvalue = None
        mock_module2.DCA.cvalue = None
        mock_module2.DCW.cvalue = None
        
        mock_model.module = [mock_module1, mock_module2]
        
        # Setup mock device
        mock_device = Mock()
        mock_device.models = {160: [mock_model]}
        mock_sunspec.return_value = mock_device
        modbus_client._device = mock_device
        modbus_client._connected = True

        # Read MPPT data
        result = modbus_client.read_mppt_data()

        # Should return data with first module working, second module zero
        assert result is not None
        assert result.mppt1.voltage == 400.5
        assert result.mppt1.current == 10.2
        assert result.mppt1.power == 4085.1
        
        assert result.mppt2.voltage == 0.0
        assert result.mppt2.current == 0.0
        assert result.mppt2.power == 0.0
        
        # Total should only include working module
        assert result.total_power == 4085.1

    def test_read_mppt_data_not_connected(self, modbus_client):
        """Test reading MPPT data when not connected."""
        result = modbus_client.read_mppt_data()
        assert result is None

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_read_mppt_data_model_160_not_available(self, mock_sunspec, modbus_client):
        """Test reading MPPT data when Model 160 is not available."""
        # Setup mock device without Model 160
        mock_device = Mock()
        mock_device.models = {1: [Mock()]}  # Only Model 1
        mock_sunspec.return_value = mock_device
        modbus_client._device = mock_device
        modbus_client._connected = True

        # Read MPPT data
        result = modbus_client.read_mppt_data()
        assert result is None

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_read_mppt_data_exception_handling(self, mock_sunspec, modbus_client):
        """Test reading MPPT data when an exception occurs."""
        # Setup mock device that raises exception on read
        mock_model = Mock()
        mock_model.read.side_effect = Exception("Read failed")
        
        mock_device = Mock()
        mock_device.models = {160: [mock_model]}
        mock_sunspec.return_value = mock_device
        modbus_client._device = mock_device
        modbus_client._connected = True

        # Read MPPT data
        result = modbus_client.read_mppt_data()
        assert result is None

    @pytest.fixture
    def mock_model_160_with_diagnostics(self):
        """Mock Model 160 with diagnostic fields available."""
        mock_model = Mock()
        mock_model.N.value = 2
        
        # Mock first module with all diagnostic fields
        mock_module1 = Mock()
        mock_module1.DCV.cvalue = 400.5
        mock_module1.DCA.cvalue = 10.2
        mock_module1.DCW.cvalue = 4085.1
        # Diagnostic fields
        mock_module1.Tmp.cvalue = 45.5  # Temperature in Celsius
        mock_module1.DCSt.value = 4     # MPPT state
        mock_module1.DCEvt.value = 0    # No events
        
        # Mock second module with some diagnostic fields unavailable
        mock_module2 = Mock()
        mock_module2.DCV.cvalue = 395.3
        mock_module2.DCA.cvalue = 9.8
        mock_module2.DCW.cvalue = 3873.94
        # Diagnostic fields - some unavailable
        mock_module2.Tmp.cvalue = None  # Temperature unavailable
        mock_module2.DCSt.value = 7     # FAULT state
        mock_module2.DCEvt.value = 129  # GROUND_FAULT (bit 0) + OVER_TEMP (bit 7)
        
        mock_model.module = [mock_module1, mock_module2]
        return mock_model

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_read_mppt_data_with_diagnostics(self, mock_sunspec, modbus_client, mock_model_160_with_diagnostics):
        """Test reading MPPT data with diagnostic fields."""
        # Setup mock device
        mock_device = Mock()
        mock_device.models = {160: [mock_model_160_with_diagnostics]}
        mock_sunspec.return_value = mock_device
        modbus_client._device = mock_device
        modbus_client._connected = True

        # Read MPPT data
        result = modbus_client.read_mppt_data()

        # Verify result
        assert result is not None
        assert isinstance(result, MPPTData)
        
        # Check that modules with diagnostics are included
        assert result.modules is not None
        assert len(result.modules) == 2
        
        # Check first module data and diagnostics
        module1 = result.modules[0]
        assert isinstance(module1, MPPTModuleData)
        assert module1.voltage == 400.5
        assert module1.current == 10.2
        assert module1.power == 4085.1
        
        # Check first module diagnostics
        diag1 = module1.diagnostics
        assert isinstance(diag1, DiagnosticData)
        assert diag1.temperature == 45.5
        assert diag1.operating_state == 4
        assert diag1.module_events == 0
        assert diag1.formatted_state == "MPPT"
        assert diag1.formatted_events == "No active events"
        
        # Check second module data and diagnostics
        module2 = result.modules[1]
        assert isinstance(module2, MPPTModuleData)
        assert module2.voltage == 395.3
        assert module2.current == 9.8
        assert module2.power == 3873.94
        
        # Check second module diagnostics (with some unavailable fields)
        diag2 = module2.diagnostics
        assert isinstance(diag2, DiagnosticData)
        assert diag2.temperature is None  # Unavailable
        assert diag2.operating_state == 7
        assert diag2.module_events == 129
        assert diag2.formatted_state == "FAULT"
        assert diag2.formatted_events == "GROUND_FAULT, OVER_TEMP"
        
        # Check backward compatibility - mppt1 and mppt2 should still work
        assert result.mppt1.voltage == 400.5
        assert result.mppt2.voltage == 395.3
        assert result.total_power == 4085.1 + 3873.94
        
        # Verify model was read
        mock_model_160_with_diagnostics.read.assert_called_once()

    @pytest.fixture
    def mock_model_160_no_diagnostic_fields(self):
        """Mock Model 160 without diagnostic fields (older firmware)."""
        mock_model = Mock()
        mock_model.N.value = 1
        
        # Mock module without diagnostic fields
        mock_module = Mock()
        mock_module.DCV.cvalue = 400.5
        mock_module.DCA.cvalue = 10.2
        mock_module.DCW.cvalue = 4085.1
        # No diagnostic fields - simulate AttributeError when accessing them
        del mock_module.Tmp
        del mock_module.DCSt
        del mock_module.DCEvt
        
        mock_model.module = [mock_module]
        return mock_model

    @patch("sunspec2.modbus.client.SunSpecModbusClientDeviceTCP")
    def test_read_mppt_data_no_diagnostic_fields(self, mock_sunspec, modbus_client, mock_model_160_no_diagnostic_fields):
        """Test reading MPPT data when diagnostic fields are not available."""
        # Setup mock device
        mock_device = Mock()
        mock_device.models = {160: [mock_model_160_no_diagnostic_fields]}
        mock_sunspec.return_value = mock_device
        modbus_client._device = mock_device
        modbus_client._connected = True

        # Read MPPT data
        result = modbus_client.read_mppt_data()

        # Verify result
        assert result is not None
        assert isinstance(result, MPPTData)
        
        # Check that modules with diagnostics are included
        assert result.modules is not None
        assert len(result.modules) == 1
        
        # Check module data
        module1 = result.modules[0]
        assert isinstance(module1, MPPTModuleData)
        assert module1.voltage == 400.5
        assert module1.current == 10.2
        assert module1.power == 4085.1
        
        # Check diagnostics - should all be None/unavailable
        diag1 = module1.diagnostics
        assert isinstance(diag1, DiagnosticData)
        assert diag1.temperature is None
        assert diag1.operating_state is None
        assert diag1.module_events is None
        assert diag1.formatted_state == "unknown"
        assert diag1.formatted_events == "unavailable"
        
        # Check backward compatibility still works
        assert result.mppt1.voltage == 400.5
        assert result.total_power == 4085.1


class TestOperatingStateFormatter:
    """Test OperatingStateFormatter functionality."""

    def test_format_valid_states(self):
        """Test formatting of valid operating state values."""
        assert OperatingStateFormatter.format_state(1) == "OFF"
        assert OperatingStateFormatter.format_state(2) == "SLEEPING"
        assert OperatingStateFormatter.format_state(3) == "STARTING"
        assert OperatingStateFormatter.format_state(4) == "MPPT"
        assert OperatingStateFormatter.format_state(5) == "THROTTLED"
        assert OperatingStateFormatter.format_state(6) == "SHUTTING_DOWN"
        assert OperatingStateFormatter.format_state(7) == "FAULT"
        assert OperatingStateFormatter.format_state(8) == "STANDBY"
        assert OperatingStateFormatter.format_state(9) == "TEST"
        assert OperatingStateFormatter.format_state(10) == "RESERVED_10"

    def test_format_invalid_states(self):
        """Test formatting of invalid operating state values."""
        assert OperatingStateFormatter.format_state(None) == "unknown"
        assert OperatingStateFormatter.format_state(0) == "unknown_0"
        assert OperatingStateFormatter.format_state(11) == "unknown_11"
        assert OperatingStateFormatter.format_state(-1) == "unknown_-1"
        assert OperatingStateFormatter.format_state(255) == "unknown_255"


class TestModuleEventsDecoder:
    """Test ModuleEventsDecoder functionality."""

    def test_decode_no_events(self):
        """Test decoding when no events are active."""
        assert ModuleEventsDecoder.decode_events(0) == "No active events"

    def test_decode_unavailable_events(self):
        """Test decoding when events data is unavailable."""
        assert ModuleEventsDecoder.decode_events(None) == "unavailable"

    def test_decode_single_events(self):
        """Test decoding single active events."""
        assert ModuleEventsDecoder.decode_events(1 << 0) == "GROUND_FAULT"
        assert ModuleEventsDecoder.decode_events(1 << 1) == "INPUT_OVER_VOLTAGE"
        assert ModuleEventsDecoder.decode_events(1 << 3) == "DC_DISCONNECT"
        assert ModuleEventsDecoder.decode_events(1 << 7) == "OVER_TEMP"
        assert ModuleEventsDecoder.decode_events(1 << 15) == "ARC_DETECTION"
        assert ModuleEventsDecoder.decode_events(1 << 22) == "INPUT_OVER_CURRENT"

    def test_decode_multiple_events(self):
        """Test decoding multiple active events."""
        # GROUND_FAULT + OVER_TEMP
        multiple_events = (1 << 0) | (1 << 7)
        result = ModuleEventsDecoder.decode_events(multiple_events)
        assert "GROUND_FAULT" in result
        assert "OVER_TEMP" in result
        assert "," in result

        # Three events: INPUT_OVER_VOLTAGE + DC_DISCONNECT + ARC_DETECTION
        three_events = (1 << 1) | (1 << 3) | (1 << 15)
        result = ModuleEventsDecoder.decode_events(three_events)
        assert "INPUT_OVER_VOLTAGE" in result
        assert "DC_DISCONNECT" in result
        assert "ARC_DETECTION" in result
        # Should have two commas for three events
        assert result.count(",") == 2

    def test_decode_unknown_bits(self):
        """Test decoding with unknown/undefined bit positions."""
        # Bit 2 is not defined in EVENT_NAMES
        unknown_bit = 1 << 2
        result = ModuleEventsDecoder.decode_events(unknown_bit)
        assert result == "No active events"

        # Mix of known and unknown bits
        mixed_events = (1 << 0) | (1 << 2) | (1 << 7)  # GROUND_FAULT + unknown + OVER_TEMP
        result = ModuleEventsDecoder.decode_events(mixed_events)
        assert "GROUND_FAULT" in result
        assert "OVER_TEMP" in result
        # Should not include unknown bit
        assert "," in result  # Should have comma for two events


class TestDiagnosticData:
    """Test DiagnosticData functionality."""

    def test_create_with_valid_data(self):
        """Test creating DiagnosticData with valid values."""
        diag_data = DiagnosticData.create(
            temperature=45.5,
            operating_state=4,  # MPPT
            module_events=1 << 7  # OVER_TEMP
        )

        assert diag_data.temperature == 45.5
        assert diag_data.operating_state == 4
        assert diag_data.module_events == 1 << 7
        assert diag_data.formatted_state == "MPPT"
        assert diag_data.formatted_events == "OVER_TEMP"

    def test_create_with_none_values(self):
        """Test creating DiagnosticData with None values."""
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

    def test_create_with_mixed_values(self):
        """Test creating DiagnosticData with mix of valid and None values."""
        diag_data = DiagnosticData.create(
            temperature=25.0,
            operating_state=None,
            module_events=0  # No events
        )

        assert diag_data.temperature == 25.0
        assert diag_data.operating_state is None
        assert diag_data.module_events == 0
        assert diag_data.formatted_state == "unknown"
        assert diag_data.formatted_events == "No active events"

    def test_create_with_invalid_state(self):
        """Test creating DiagnosticData with invalid operating state."""
        diag_data = DiagnosticData.create(
            temperature=30.0,
            operating_state=99,  # Invalid state
            module_events=0
        )

        assert diag_data.temperature == 30.0
        assert diag_data.operating_state == 99
        assert diag_data.module_events == 0
        assert diag_data.formatted_state == "unknown_99"
        assert diag_data.formatted_events == "No active events"

    def test_create_with_multiple_events(self):
        """Test creating DiagnosticData with multiple active events."""
        # GROUND_FAULT + INPUT_OVER_VOLTAGE + OVER_TEMP
        events_bitfield = (1 << 0) | (1 << 1) | (1 << 7)
        
        diag_data = DiagnosticData.create(
            temperature=75.0,
            operating_state=7,  # FAULT
            module_events=events_bitfield
        )

        assert diag_data.temperature == 75.0
        assert diag_data.operating_state == 7
        assert diag_data.module_events == events_bitfield
        assert diag_data.formatted_state == "FAULT"
        
        # Check that all three events are in the formatted string
        formatted_events = diag_data.formatted_events
        assert "GROUND_FAULT" in formatted_events
        assert "INPUT_OVER_VOLTAGE" in formatted_events
        assert "OVER_TEMP" in formatted_events
        assert formatted_events.count(",") == 2  # Two commas for three events