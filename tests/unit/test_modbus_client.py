"""
Tests for ModbusClient MPPT data reading functionality.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from fronius_modbus.modbus_client import ModbusClient, MPPTChannelData, MPPTData


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