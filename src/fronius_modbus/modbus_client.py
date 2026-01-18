"""Modbus client for Fronius Symo inverters using pysunspec2."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import sunspec2.modbus.client as modbus_client

logger = logging.getLogger(__name__)


@dataclass
class MPPTChannelData:
    """Data for a single MPPT channel."""

    voltage: float  # Volts
    current: float  # Amps
    power: float  # Watts


@dataclass
class MPPTData:
    """Complete MPPT data from inverter."""

    mppt1: MPPTChannelData
    mppt2: MPPTChannelData
    total_power: float  # Total DC power in Watts
    timestamp: datetime


class ModbusClient:
    """Modbus client for reading SunSpec Model 160 data from Fronius inverters."""

    def __init__(self, host: str, port: int, unit_id: int, timeout: int) -> None:
        """
        Initialize ModbusClient with connection parameters.

        Args:
            host: IP address of the Fronius inverter
            port: Modbus TCP port (typically 502)
            unit_id: Modbus unit ID (slave ID)
            timeout: Connection timeout in seconds
        """
        self._host = host
        self._port = port
        self._unit_id = unit_id
        self._timeout = timeout
        self._device: Optional[modbus_client.SunSpecModbusClientDeviceTCP] = None
        self._connected = False

    def connect(self) -> bool:
        """
        Attempt connection to the inverter and perform device scan.

        Returns:
            True if connection and scan successful, False otherwise
        """
        try:
            logger.info(
                f"Attempting Modbus connection to {self._host}:{self._port} "
                f"(unit_id={self._unit_id})"
            )

            # Create pysunspec2 device instance
            self._device = modbus_client.SunSpecModbusClientDeviceTCP(
                slave_id=self._unit_id,
                ipaddr=self._host,
                ipport=self._port,
                timeout=self._timeout,
            )

            # Perform device scan to discover available models
            self._device.scan()

            self._connected = True
            logger.info("Modbus connection established successfully")
            return True

        except Exception as e:
            logger.error(f"Modbus connection failed: {e}")
            self._connected = False
            self._device = None
            return False

    def disconnect(self) -> None:
        """Disconnect from the inverter."""
        if self._device:
            try:
                self._device.close()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._device = None
                self._connected = False
                logger.info("Modbus connection closed")

    def is_connected(self) -> bool:
        """
        Check if connected to the inverter.

        Returns:
            True if connected, False otherwise
        """
        return self._connected

    def verify_model_160(self) -> bool:
        """
        Verify that SunSpec Model 160 is available on the device.

        Returns:
            True if Model 160 is found, False otherwise
        """
        if not self._device:
            logger.error("Cannot verify Model 160: not connected")
            return False

        try:
            # Check if Model 160 exists in discovered models
            if 160 in self._device.models:
                logger.info("SunSpec Model 160 (Multiple MPPT Inverter Extension) found")
                return True
            else:
                logger.warning("SunSpec Model 160 not found on device")
                return False

        except Exception as e:
            logger.error(f"Error verifying Model 160: {e}")
            return False

    def read_device_info(self) -> Optional[Dict[str, str]]:
        """
        Read device identification information from Model 1 (Common Model).

        Returns:
            Dictionary with manufacturer, model, and serial_number, or None if unavailable
        """
        if not self._device:
            logger.error("Cannot read device info: not connected")
            return None

        try:
            # Check if Model 1 (Common Model) is available
            if 1 not in self._device.models:
                logger.warning("Model 1 (Common Model) not available")
                return None

            # Access Model 1
            common_model = self._device.models[1][0]

            # Read current values from the device
            common_model.read()

            # Extract device information using .cvalue (computed/scaled value)
            device_info = {
                "manufacturer": common_model.Mn.cvalue,
                "model": common_model.Md.cvalue,
                "serial_number": common_model.SN.cvalue,
            }

            logger.info(
                f"Device info: {device_info['manufacturer']} {device_info['model']} "
                f"(S/N: {device_info['serial_number']})"
            )

            return device_info

        except Exception as e:
            logger.error(f"Error reading device info: {e}")
            return None

    def read_mppt_data(self) -> Optional[MPPTData]:
        """
        Read MPPT data from Model 160.

        Returns:
            MPPTData object with voltage, current, and power for both MPPT channels,
            or None if read fails
        """
        if not self._device:
            logger.error("Cannot read MPPT data: not connected")
            return None

        try:
            # Check if Model 160 is available
            if 160 not in self._device.models:
                logger.error("Model 160 not available")
                return None

            # Access Model 160
            model_160 = self._device.models[160][0]

            # Read current values from the device
            model_160.read()

            # Check number of available MPPT modules
            num_modules = model_160.N.value
            logger.debug(f"Number of MPPT modules available: {num_modules}")

            if num_modules < 1:
                logger.error("No MPPT modules available")
                return None

            # Read MPPT module data dynamically
            mppt_channels = []
            total_power = 0.0

            for i in range(num_modules):
                try:
                    voltage = float(model_160.module[i].DCV.cvalue) if model_160.module[i].DCV.cvalue is not None else 0.0
                    current = float(model_160.module[i].DCA.cvalue) if model_160.module[i].DCA.cvalue is not None else 0.0
                    power = float(model_160.module[i].DCW.cvalue) if model_160.module[i].DCW.cvalue is not None else 0.0
                    
                    mppt_channel = MPPTChannelData(
                        voltage=voltage,
                        current=current,
                        power=power
                    )
                    mppt_channels.append(mppt_channel)
                    total_power += power
                    
                    logger.debug(f"MPPT{i+1}: {voltage}V, {current}A, {power}W")
                    
                except Exception as e:
                    logger.warning(f"Error reading MPPT module {i}: {e}")
                    # Add empty channel data for failed reads
                    mppt_channels.append(MPPTChannelData(voltage=0.0, current=0.0, power=0.0))

            # Ensure we have at least 2 channels for backward compatibility
            # If we have fewer than 2 modules, pad with empty data
            while len(mppt_channels) < 2:
                mppt_channels.append(MPPTChannelData(voltage=0.0, current=0.0, power=0.0))

            # Create MPPTData object with first two channels for backward compatibility
            mppt_data = MPPTData(
                mppt1=mppt_channels[0],
                mppt2=mppt_channels[1],
                total_power=total_power,
                timestamp=datetime.now(),
            )

            logger.debug(
                f"MPPT data read: MPPT1={mppt_channels[0].power}W, MPPT2={mppt_channels[1].power}W, "
                f"Total={total_power}W"
            )

            return mppt_data

        except Exception as e:
            logger.error(f"Error reading MPPT data: {e}")
            return None
