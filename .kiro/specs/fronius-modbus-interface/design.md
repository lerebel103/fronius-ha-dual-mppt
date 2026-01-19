# Design Document: Fronius Modbus Interface

## Overview

This system is a Python-based bridge that connects Fronius Symo solar inverters to Home Assistant via MQTT. It uses the pysunspec2 library to communicate with the inverter over Modbus TCP, reads SunSpec Model 160 data for MPPT channels, and publishes the data to an MQTT broker using Home Assistant's auto-discovery protocol.

The application runs as a containerized service, polling the inverter every 5 seconds and publishing voltage, current, and power readings for both MPPT1 and MPPT2 channels. The pysunspec2 library handles all Modbus communication details and automatically applies SunSpec scaling factors.

## Architecture

The system follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────┐
│         Main Application Loop           │
│  (Orchestration & Error Handling)       │
└─────────────────────────────────────────┘
           │              │
           ▼              ▼
┌──────────────────┐  ┌──────────────────┐
│  Modbus Client   │  │  MQTT Publisher  │
│  (pysunspec2)    │  │  (paho-mqtt)     │
└──────────────────┘  └──────────────────┘
           │              │
           ▼              ▼
┌──────────────────┐  ┌──────────────────┐
│ Fronius Inverter │  │   MQTT Broker    │
│  (SunSpec 160)   │  │ (Home Assistant) │
└──────────────────┘  └──────────────────┘
```

### Key Components

1. **Configuration Manager**: Loads and validates YAML configuration
2. **Modbus Client**: Manages connection to inverter using pysunspec2 and reads Model 160 data
3. **Data Extractor**: Extracts scaled MPPT data from pysunspec2 model objects
4. **MQTT Publisher**: Publishes discovery messages and sensor data
5. **Main Loop**: Orchestrates polling, error handling, and reconnection logic

## Components and Interfaces

### 1. Configuration Manager

**Purpose**: Load, validate, and provide access to configuration parameters

**Interface**:
```python
class Config:
    def __init__(self, config_path: str)
    def validate(self) -> bool
    
    # Modbus properties
    @property
    def modbus_host(self) -> str
    @property
    def modbus_port(self) -> int
    @property
    def modbus_unit_id(self) -> int
    @property
    def modbus_timeout(self) -> int
    
    # MQTT properties
    @property
    def mqtt_broker(self) -> str
    @property
    def mqtt_port(self) -> int
    @property
    def mqtt_username(self) -> str
    @property
    def mqtt_password(self) -> str
    @property
    def mqtt_client_id(self) -> str
    @property
    def mqtt_topic_prefix(self) -> str
    
    # Application properties
    @property
    def poll_interval(self) -> int
    @property
    def log_level(self) -> str
```

**Configuration File Format** (config.yaml):
```yaml
modbus:
  host: "192.168.1.100"
  port: 502
  unit_id: 1
  timeout: 10

mqtt:
  broker: "192.168.1.50"
  port: 1883
  username: "homeassistant"
  password: "secret"
  client_id: "fronius_bridge"
  topic_prefix: "homeassistant"

application:
  poll_interval: 5
  log_level: "INFO"
```

### 2. Modbus Client

**Purpose**: Establish connection to Fronius inverter and read SunSpec Model 160 data using pysunspec2

**Interface**:
```python
class ModbusClient:
    def __init__(self, host: str, port: int, unit_id: int, timeout: int)
    def connect(self) -> bool
    def disconnect(self) -> None
    def is_connected(self) -> bool
    def verify_model_160(self) -> bool
    def read_device_info(self) -> Optional[Dict[str, str]]
    def read_mppt_data(self) -> Optional[MPPTData]
```

**Implementation Details**:
- Uses pysunspec2 library's `SunSpecModbusClientDeviceTCP` class
- Calls `device.scan()` to discover available models
- Accesses Model 160 via `device.models[160][0]` or by model name
- Reads device info from Model 1 (Common Model) via `device.models[1][0]`
- Reads data using `model.read()` method
- Extracts scaled values using point `.cvalue` attribute (pysunspec2 handles scaling automatically)
- Implements exponential backoff for reconnection (1s, 2s, 4s, 8s, max 60s)
- Validates Model 160 presence after scan

**pysunspec2 Usage Pattern**:
```python
import sunspec2.modbus.client as client

# Create device
device = client.SunSpecModbusClientDeviceTCP(
    slave_id=unit_id,
    ipaddr=host,
    ipport=port
)

# Discover models
device.scan()

# Check for Model 160
if 160 not in device.models:
    raise ModelNotFoundError("Model 160 not found")

# Read device information from Model 1 (Common Model)
device_info = None
if 1 in device.models:
    common_model = device.models[1][0]
    common_model.read()
    
    device_info = {
        "manufacturer": common_model.Mn.cvalue,
        "model": common_model.Md.cvalue,
        "serial_number": common_model.SN.cvalue
    }

# Access Model 160
model_160 = device.models[160][0]

# Read current values
model_160.read()

# Dynamic MPPT module reading
num_modules = model_160.N.value  # Number of available MPPT modules

# Read each MPPT module dynamically
for i in range(num_modules):
    voltage = model_160.module[i].DCV.cvalue  # DC Voltage
    current = model_160.module[i].DCA.cvalue  # DC Current  
    power = model_160.module[i].DCW.cvalue    # DC Power
```

### 3. Data Extractor

**Purpose**: Extract and format MPPT data from pysunspec2 model objects

**Interface**:
```python
@dataclass
class MPPTChannelData:
    voltage: float  # Volts (already scaled by pysunspec2)
    current: float  # Amps (already scaled by pysunspec2)
    power: float    # Watts (already scaled by pysunspec2)

@dataclass
class MPPTData:
    mppt1: MPPTChannelData
    mppt2: MPPTChannelData
    timestamp: datetime

class DataExtractor:
    @staticmethod
    def extract_mppt_data(model_160) -> MPPTData
```

**Data Extraction**:
- pysunspec2 automatically applies scaling factors via the `.cvalue` attribute
- First check `model_160.N.value` to determine the number of available MPPT modules
- Dynamically access each module using `model_160.module[i]` where `i` ranges from 0 to `N-1`
- For each module, read: `DCV.cvalue` (voltage), `DCA.cvalue` (current), `DCW.cvalue` (power)
- No manual scaling calculation needed - pysunspec2 handles this internally
- Calculate total power by summing power from all available modules
- Maintain backward compatibility by ensuring at least 2 MPPT channels in result (pad with zeros if needed)

**Dynamic Module Reading**:
The system supports inverters with varying numbers of MPPT modules:
- Single MPPT: Only MPPT1 populated, MPPT2 set to zero values
- Dual MPPT: Both MPPT1 and MPPT2 populated from respective modules
- Multiple MPPT: First two modules mapped to MPPT1/MPPT2 for backward compatibility
- Error handling: Individual module read failures result in zero values for that module

### 4. MQTT Publisher

**Purpose**: Publish Home Assistant discovery messages and sensor data

**Interface**:
```python
class MQTTPublisher:
    def __init__(self, broker: str, port: int, username: str, password: str, 
                 client_id: str, topic_prefix: str)
    def connect(self) -> bool
    def disconnect(self) -> None
    def is_connected(self) -> bool
    def publish_discovery(self, device_info: Dict) -> bool
    def publish_sensor_data(self, mppt_data: MPPTData) -> bool
```

**MQTT Topics**:
- Discovery: `{topic_prefix}/sensor/fronius_{serial}/mppt{N}_{metric}/config`
- State: `{topic_prefix}/sensor/fronius_{serial}/mppt{N}_{metric}/state`

**Discovery Message Format**:
```json
{
  "name": "Fronius MPPT1 Voltage",
  "unique_id": "fronius_{serial}_mppt1_voltage",
  "state_topic": "homeassistant/sensor/fronius_{serial}/mppt1_voltage/state",
  "unit_of_measurement": "V",
  "device_class": "voltage",
  "state_class": "measurement",
  "value_template": "{{ value_json.voltage }}",
  "device": {
    "identifiers": ["fronius_{serial}"],
    "name": "{manufacturer} {model}",
    "manufacturer": "{manufacturer}",
    "model": "{model}",
    "serial_number": "{serial}"
  }
}
```

**Device Information Extraction**:
The device information (manufacturer, model, serial number) should be read from SunSpec Common Model (Model 1):

```python
# After device.scan()
if 1 in device.models:
    common_model = device.models[1][0]
    common_model.read()
    
    manufacturer = common_model.Mn.cvalue  # Manufacturer
    model = common_model.Md.cvalue         # Model
    serial = common_model.SN.cvalue        # Serial Number
    
    device_info = {
        "identifiers": [f"fronius_{serial}"],
        "name": f"{manufacturer} {model}",
        "manufacturer": manufacturer,
        "model": model,
        "serial_number": serial
    }
```

### 5. Main Application Loop

**Purpose**: Orchestrate polling, error handling, and reconnection

**Pseudocode**:
```
function main():
    config = load_config(args.config_path)
    setup_logging(config.log_level)
    
    modbus_client = ModbusClient(config.modbus_*)
    mqtt_publisher = MQTTPublisher(config.mqtt_*)
    
    modbus_connected = False
    mqtt_connected = False
    model_160_verified = False
    device_info = None
    
    # Main polling loop with resilient connection handling
    while True:
        try:
            # Attempt Modbus connection if not connected
            if not modbus_connected:
                if modbus_client.connect():
                    log_info("Modbus connected successfully")
                    modbus_connected = True
                    
                    # Verify Model 160 after connection
                    if modbus_client.verify_model_160():
                        log_info("Model 160 found")
                        model_160_verified = True
                        
                        # Read device info from Model 1
                        device_info = modbus_client.read_device_info()
                    else:
                        log_warning("Model 160 not found, will retry")
                        modbus_connected = False
                else:
                    log_error("Modbus connection failed, will retry")
                    sleep(config.poll_interval)
                    continue
            
            # Attempt MQTT connection if not connected
            if not mqtt_connected:
                if mqtt_publisher.connect():
                    log_info("MQTT connected successfully")
                    mqtt_connected = True
                    
                    # Publish discovery messages when MQTT connects
                    if device_info:
                        mqtt_publisher.publish_discovery(device_info)
                else:
                    log_error("MQTT connection failed, will retry")
            
            # Only poll data if both connections are established and Model 160 is verified
            if modbus_connected and model_160_verified:
                mppt_data = modbus_client.read_mppt_data()
                
                if mppt_data and mqtt_connected:
                    mqtt_publisher.publish_sensor_data(mppt_data)
                elif not mppt_data:
                    log_warning("Failed to read MPPT data")
                    modbus_connected = False  # Trigger reconnection
            
            sleep(config.poll_interval)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            log_error(f"Error in main loop: {e}")
            # Reset connection states on unexpected errors
            modbus_connected = False
            mqtt_connected = False
            sleep(config.poll_interval)
    
    # Cleanup
    modbus_client.disconnect()
    mqtt_publisher.disconnect()
```

## Data Models

### SunSpec Model 160

Model 160 (Multiple MPPT Inverter Extension) provides detailed DC input data for each MPPT channel. The pysunspec2 library:
- Automatically discovers the model structure
- Reads all registers in a single operation
- Applies scaling factors internally
- Provides scaled values via the `.cvalue` attribute on each point

**Dynamic Module Access**:
- `model_160.N.value`: Number of available MPPT modules (integer)
- `model_160.module[i]`: Access to individual MPPT module where `i` is 0-based index
- Each module provides: `DCV.cvalue` (voltage), `DCA.cvalue` (current), `DCW.cvalue` (power)

**Key Points** (accessed via `model_160.module[i].{point}.cvalue`):
- `DCV`: MPPT channel DC voltage (V)
- `DCA`: MPPT channel DC current (A)  
- `DCW`: MPPT channel DC power (W)

### Internal Data Structures

```python
@dataclass
class MPPTChannelData:
    """Data for a single MPPT channel"""
    voltage: float  # Volts
    current: float  # Amps
    power: float    # Watts

@dataclass
class MPPTData:
    """Complete MPPT data from inverter"""
    mppt1: MPPTChannelData
    mppt2: MPPTChannelData
    total_power: float    # Total DC power from all modules
    timestamp: datetime
    
@dataclass
class ConnectionState:
    """Track connection states"""
    modbus_connected: bool
    mqtt_connected: bool
    last_modbus_attempt: datetime
    last_mqtt_attempt: datetime
    modbus_retry_delay: int  # seconds
    mqtt_retry_delay: int    # seconds
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: MPPT Data Extraction

*For any* valid Model 160 object from pysunspec2 with N available modules, extracting MPPT data should:
- Read the number of modules from `model_160.N.value`
- Successfully extract voltage, current, and power values from each module using `model_160.module[i].{DCV,DCA,DCW}.cvalue`
- Calculate total power as the sum of all module powers
- Map the first module to MPPT1 and second module (if available) to MPPT2
- Provide zero values for MPPT2 if only one module is available

**Validates: Requirements 3.2, 3.3, 3.4**

### Property 2: MQTT Topic Structure

*For any* MPPT channel (1 or 2) and metric type (voltage, current, power), the generated MQTT state topic should follow the pattern `{prefix}/sensor/{device_id}/mppt{N}_{metric}/state`.

**Validates: Requirements 6.2, 6.3**

### Property 3: MQTT Payload Contains Numeric Values

*For any* MPPT data, the generated MQTT payload should contain numeric values for voltage, current, and power that can be parsed as floats.

**Validates: Requirements 6.5**

### Property 4: MQTT Payload Contains Timestamp

*For any* MPPT data, the generated MQTT payload should include a timestamp field with valid ISO 8601 format.

**Validates: Requirements 6.6**

### Property 5: Home Assistant Discovery Format

*For any* sensor configuration (MPPT channel and metric type), the generated discovery message should be valid JSON containing required fields: name, unique_id, state_topic, unit_of_measurement, device_class, state_class, and device information.

**Validates: Requirements 8.2, 8.5, 8.6**

### Property 6: Discovery State Class

*For any* sensor discovery message, the state_class field should be set to "measurement".

**Validates: Requirements 8.6**

### Property 7: Device Information from Model 1

*For any* device with Model 1 available, the device information should include manufacturer, model, and serial_number extracted from Model 1 points.

**Validates: Requirements 3.2, 3.3, 3.4, 8.9, 8.10**

### Property 8: Discovery Messages for All Sensors

*For any* device configuration, the system should generate exactly 6 discovery messages (3 metrics × 2 MPPT channels: voltage, current, power for MPPT1 and MPPT2).

**Validates: Requirements 8.3, 8.4**

### Property 9: Discovery Topic Pattern

*For any* sensor, the discovery topic should follow the pattern `{prefix}/sensor/{device_id}/{sensor_id}/config`.

**Validates: Requirements 8.7**

### Property 10: Device Grouping in Discovery

*For any* set of discovery messages, all messages should reference the same device identifier in their device information section.

**Validates: Requirements 8.8**

### Property 11: Invalid Data Detection

*For any* malformed or out-of-range data from pysunspec2 (including cases where `model_160.N.value` is 0 or module access fails), the validation function should detect it as invalid and handle gracefully by returning appropriate error states or zero values.

**Validates: Requirements 9.2**

### Property 12: Error Classification

*For any* error type (network timeout, connection refused, invalid credentials, malformed data), the system should correctly classify it as either a temporary network error or a configuration error.

**Validates: Requirements 9.5**

### Property 13: Configuration Parsing

*For any* valid YAML configuration file, the parser should successfully extract all required parameters without errors.

**Validates: Requirements 10.1**

### Property 14: Configuration Validation

*For any* configuration object, validation should verify the presence of all required fields: Modbus parameters (host, port, unit_id, timeout), MQTT parameters (broker, port, username, password, client_id, topic_prefix), and application parameters (poll_interval, log_level).

**Validates: Requirements 10.4, 10.5, 10.6, 10.7, 10.8, 10.9**

### Property 15: Invalid Configuration Error Messages

*For any* configuration with missing or invalid parameters, the validation function should return an error message that identifies which specific parameter is problematic.

**Validates: Requirements 10.10**

## Error Handling

### Connection Errors

**Modbus Connection Failures**:
- Initial connection failure: Log error and retry with exponential backoff
- Connection loss during operation: Log error, implement exponential backoff (1s, 2s, 4s, 8s, max 60s)
- Continue attempting reconnection indefinitely
- When reconnected, verify Model 160 and resume normal polling

**MQTT Connection Failures**:
- Initial connection failure: Log error and retry with exponential backoff
- Connection loss during operation: Log error, implement exponential backoff (1s, 2s, 4s, 8s, max 60s)
- Continue Modbus polling even if MQTT is disconnected
- When MQTT reconnects, republish all discovery messages

### Data Errors

**Invalid Data from pysunspec2**:
- Check if model read was successful
- Validate that `model_160.N.value` is greater than 0
- For each module, validate that `.cvalue` attributes are not None
- Handle individual module read failures gracefully (continue with other modules)
- Validate values are within expected ranges
- Log error and skip publishing for invalid data
- Continue polling on next cycle

**Model 160 Not Found**:
- Log warning message: "SunSpec Model 160 not found, will retry"
- Continue attempting to scan and discover models
- Do not exit - keep retrying indefinitely

### Configuration Errors

**Invalid Configuration**:
- Missing required parameters: Log specific missing field, exit with code 1
- Invalid parameter values: Log specific invalid field and reason, exit with code 1
- Malformed YAML: Log parse error, exit with code 1

**File Not Found**:
- Default config path: Log error with expected path, exit with code 1
- Custom config path (--config): Log error with provided path, exit with code 1

## Testing Strategy

This project will use a dual testing approach combining unit tests and property-based tests to ensure comprehensive coverage and correctness.

### Unit Testing

Unit tests will focus on:
- **Specific examples**: Verify correct behavior with known good inputs
- **Edge cases**: Empty configs, boundary values, special characters
- **Integration points**: Component interactions, error propagation
- **Error conditions**: Specific failure scenarios

Example unit tests:
- Test config loading with valid YAML file
- Test Model 160 verification with correct/incorrect model ID
- Test MQTT discovery message generation for MPPT1 voltage sensor
- Test exponential backoff calculation for specific retry counts
- Test error handling when Modbus connection fails

### Property-Based Testing

Property-based tests will verify universal properties across many generated inputs using the **Hypothesis** library for Python.

**Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with: `# Feature: fronius-modbus-interface, Property N: [property text]`

**Test Coverage**:

1. **Data Extraction (Property 1)**
   - Generate mock pysunspec2 Model 160 objects with random `N.value` (0-4 modules)
   - Generate random module data with `.cvalue` attributes
   - Verify: Extracted data handles variable number of modules correctly
   - Verify: MPPT1 and MPPT2 mapping works for 1, 2, or more modules
   - Verify: Total power calculation sums all available modules

2. **MQTT Topics (Properties 2, 7)**
   - Generate random device IDs, sensor IDs, prefixes
   - Verify: Topics match expected patterns

3. **MQTT Payloads (Properties 3, 4)**
   - Generate random MPPT data
   - Verify: Payloads contain numeric values and valid timestamps

4. **Discovery Messages (Properties 5, 6, 8)**
   - Generate random sensor configurations
   - Verify: Messages are valid JSON with required fields
   - Verify: Correct number of messages generated
   - Verify: All messages reference same device

5. **Validation (Properties 9, 10, 12, 13)**
   - Generate random invalid data and configs
   - Verify: Validation catches errors
   - Verify: Error messages identify problems
   - Verify: Errors classified correctly

**Generator Strategies**:
- Mock pysunspec2 objects with random `N.value` (0-4) and corresponding module arrays
- Mock modules with random `.cvalue` attributes for DCV, DCA, DCW
- Valid configs: YAML with all required fields and valid values
- Invalid configs: Missing fields, invalid types, out-of-range values
- MPPT data: Random floats for voltage (0-1000V), current (0-50A), power (0-10000W)
- Edge cases: Zero modules, single module, module read failures (None values)

### Integration Testing

Integration tests will verify:
- End-to-end flow from config loading to MQTT publishing
- Reconnection behavior with simulated network failures
- Docker container startup and configuration via environment variables
- Interaction with actual pysunspec2 library (using test fixtures or mock devices)

### Test Execution

- Unit tests: Run with `pytest tests/unit/`
- Property tests: Run with `pytest tests/property/` (tagged with `@pytest.mark.property`)
- Integration tests: Run with `pytest tests/integration/`
- All tests: Run with `make test`

Property-based tests will use Hypothesis's example database to remember failing cases and regression test them automatically.
