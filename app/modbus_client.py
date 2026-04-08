"""Modbus client for Fronius Symo inverters using pysunspec2."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

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
    
    # New diagnostic data for all modules
    modules: Optional[List['MPPTModuleData']] = None  # All available modules with diagnostics


class OperatingStateFormatter:
    """Formats operating state enum values to human-readable strings."""
    
    STATE_NAMES = {
        1: "OFF",
        2: "SLEEPING", 
        3: "STARTING",
        4: "MPPT",
        5: "THROTTLED",
        6: "SHUTTING_DOWN",
        7: "FAULT",
        8: "STANDBY",
        9: "TEST",
        10: "RESERVED_10"
    }
    
    @classmethod
    def format_state(cls, state_value: Optional[int]) -> str:
        """Convert state enum to human-readable string."""
        if state_value is None:
            return "unknown"
        return cls.STATE_NAMES.get(state_value, f"unknown_{state_value}")


class ModuleEventsDecoder:
    """Decodes module events bitfield into human-readable event names."""
    
    EVENT_NAMES = {
        0: "GROUND_FAULT",
        1: "INPUT_OVER_VOLTAGE", 
        3: "DC_DISCONNECT",
        5: "CABINET_OPEN",
        6: "MANUAL_SHUTDOWN",
        7: "OVER_TEMP",
        12: "BLOWN_FUSE",
        13: "UNDER_TEMP",
        14: "MEMORY_LOSS",
        15: "ARC_DETECTION",
        20: "TEST_FAILED",
        21: "INPUT_UNDER_VOLTAGE",
        22: "INPUT_OVER_CURRENT"
    }
    
    @classmethod
    def decode_events(cls, events_bitfield: Optional[int]) -> str:
        """Decode bitfield into comma-separated list of active events."""
        if events_bitfield is None:
            return "unavailable"
        
        if events_bitfield == 0:
            return "No active events"
        
        active_events = []
        for bit_position, event_name in cls.EVENT_NAMES.items():
            if events_bitfield & (1 << bit_position):
                active_events.append(event_name)
        
        return ", ".join(active_events) if active_events else "No active events"


@dataclass
class DiagnosticData:
    """Diagnostic data for a single MPPT module."""
    temperature: Optional[float]  # Celsius, None if unavailable
    operating_state: Optional[int]  # Enum value, None if unavailable
    module_events: Optional[int]  # Bitfield, None if unavailable
    
    # Formatted versions for display
    formatted_state: str
    formatted_events: str
    
    @classmethod
    def create(cls, temperature: Optional[float], operating_state: Optional[int], 
               module_events: Optional[int]) -> 'DiagnosticData':
        """Create DiagnosticData with formatted versions."""
        return cls(
            temperature=temperature,
            operating_state=operating_state,
            module_events=module_events,
            formatted_state=OperatingStateFormatter.format_state(operating_state),
            formatted_events=ModuleEventsDecoder.decode_events(module_events)
        )


@dataclass
class MPPTModuleData:
    """Complete data for a single MPPT module including diagnostics."""
    # Power data
    voltage: float
    current: float
    power: float
    
    # Diagnostic data
    diagnostics: DiagnosticData


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
        Read MPPT data from Model 160, including diagnostic fields.

        Returns:
            MPPTData object with voltage, current, and power for both MPPT channels,
            plus diagnostic data for all modules, or None if read fails
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

            # Read MPPT module data dynamically with diagnostics
            mppt_channels = []
            modules_with_diagnostics = []
            total_power = 0.0

            for i in range(num_modules):
                try:
                    # Read power data
                    voltage = float(model_160.module[i].DCV.cvalue) if model_160.module[i].DCV.cvalue is not None else 0.0
                    current = float(model_160.module[i].DCA.cvalue) if model_160.module[i].DCA.cvalue is not None else 0.0
                    power = float(model_160.module[i].DCW.cvalue) if model_160.module[i].DCW.cvalue is not None else 0.0
                    
                    # Read diagnostic data - handle cases where fields may be unavailable
                    temperature = None
                    operating_state = None
                    module_events = None
                    
                    try:
                        # Temperature: use .cvalue for scaled value in Celsius
                        if hasattr(model_160.module[i], 'Tmp') and model_160.module[i].Tmp.cvalue is not None:
                            temperature = float(model_160.module[i].Tmp.cvalue)
                    except (AttributeError, ValueError, TypeError) as e:
                        logger.debug(f"Temperature field unavailable for module {i}: {e}")
                    
                    try:
                        # Operating State: use .value for raw enum value
                        if hasattr(model_160.module[i], 'DCSt') and model_160.module[i].DCSt.value is not None:
                            operating_state = int(model_160.module[i].DCSt.value)
                    except (AttributeError, ValueError, TypeError) as e:
                        logger.debug(f"Operating state field unavailable for module {i}: {e}")
                    
                    try:
                        # Module Events: use .value for raw bitfield value
                        if hasattr(model_160.module[i], 'DCEvt') and model_160.module[i].DCEvt.value is not None:
                            module_events = int(model_160.module[i].DCEvt.value)
                    except (AttributeError, ValueError, TypeError) as e:
                        logger.debug(f"Module events field unavailable for module {i}: {e}")
                    
                    # Create diagnostic data with formatted versions
                    diagnostic_data = DiagnosticData.create(
                        temperature=temperature,
                        operating_state=operating_state,
                        module_events=module_events
                    )
                    
                    # Create MPPT channel data for backward compatibility
                    mppt_channel = MPPTChannelData(
                        voltage=voltage,
                        current=current,
                        power=power
                    )
                    mppt_channels.append(mppt_channel)
                    
                    # Create module data with diagnostics
                    module_data = MPPTModuleData(
                        voltage=voltage,
                        current=current,
                        power=power,
                        diagnostics=diagnostic_data
                    )
                    modules_with_diagnostics.append(module_data)
                    
                    total_power += power
                    
                    logger.debug(f"MPPT{i+1}: {voltage}V, {current}A, {power}W, "
                               f"Temp: {temperature}°C, State: {diagnostic_data.formatted_state}, "
                               f"Events: {diagnostic_data.formatted_events}")
                    
                except Exception as e:
                    logger.warning(f"Error reading MPPT module {i}: {e}")
                    # Add empty channel data for failed reads
                    mppt_channels.append(MPPTChannelData(voltage=0.0, current=0.0, power=0.0))
                    # Add module with empty diagnostics
                    empty_diagnostics = DiagnosticData.create(None, None, None)
                    modules_with_diagnostics.append(MPPTModuleData(
                        voltage=0.0, current=0.0, power=0.0, diagnostics=empty_diagnostics
                    ))

            # Ensure we have at least 2 channels for backward compatibility
            # If we have fewer than 2 modules, pad with empty data
            while len(mppt_channels) < 2:
                mppt_channels.append(MPPTChannelData(voltage=0.0, current=0.0, power=0.0))

            # Create MPPTData object with first two channels for backward compatibility
            # and include all modules with diagnostics
            mppt_data = MPPTData(
                mppt1=mppt_channels[0],
                mppt2=mppt_channels[1],
                total_power=total_power,
                timestamp=datetime.now(),
                modules=modules_with_diagnostics
            )

            logger.debug(
                f"MPPT data read: MPPT1={mppt_channels[0].power}W, MPPT2={mppt_channels[1].power}W, "
                f"Total={total_power}W, Modules with diagnostics: {len(modules_with_diagnostics)}"
            )

            return mppt_data

        except Exception as e:
            logger.error(f"Error reading MPPT data: {e}")
            return None
