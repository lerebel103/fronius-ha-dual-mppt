# Design Document: Diagnostic Sensors

## Overview

This feature extends the existing Fronius Modbus interface to expose additional diagnostic sensors from SunSpec Model 160. The implementation adds Temperature (Tmp), Operating State (DCSt), and Module Events (DCEvt) sensors for each MPPT module as diagnostic sensors in Home Assistant. These sensors provide deeper insights into system health and operational status while maintaining the existing architecture and performance characteristics.

The diagnostic sensors follow Home Assistant conventions by being disabled by default (except Operating State), using appropriate device classes, and providing human-readable values. The implementation leverages the existing pysunspec2 integration and MQTT infrastructure, requiring minimal changes to the core polling and connection management logic.

## Architecture

The diagnostic sensors integrate seamlessly into the existing layered architecture:

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
│ + Diagnostic     │  │ + Diagnostic     │
│   Data Reader    │  │   Sensors        │
└──────────────────┘  └──────────────────┘
           │              │
           ▼              ▼
┌──────────────────┐  ┌──────────────────┐
│ Fronius Inverter │  │   MQTT Broker    │
│  (SunSpec 160)   │  │ (Home Assistant) │
│ + Tmp, DCSt,     │  │ + Diagnostic     │
│   DCEvt fields   │  │   Entities       │
└──────────────────┘  └──────────────────┘
```

### New Components

1. **Diagnostic Data Reader**: Extracts Tmp, DCSt, and DCEvt fields from Model 160
2. **Operating State Formatter**: Converts numeric state values to human-readable names
3. **Module Events Decoder**: Decodes bitfield into active event names
4. **Diagnostic Sensor Factory**: Creates diagnostic sensor configurations for Home Assistant
5. **Enhanced MQTT Publisher**: Publishes diagnostic sensor discovery and data

## Components and Interfaces

### 1. Enhanced Modbus Client

**Purpose**: Extend existing ModbusClient to read diagnostic fields from Model 160

**New Interface Methods**:
```python
@dataclass
class DiagnosticData:
    """Diagnostic data for a single MPPT module."""
    temperature: Optional[float]  # Celsius, None if unavailable
    operating_state: Optional[int]  # Enum value, None if unavailable
    module_events: Optional[int]  # Bitfield, None if unavailable

@dataclass
class MPPTModuleData:
    """Complete data for a single MPPT module."""
    # Existing fields
    voltage: float
    current: float
    power: float
    # New diagnostic fields
    diagnostics: DiagnosticData

class ModbusClient:
    # Existing methods unchanged
    def read_mppt_data(self) -> Optional[MPPTData]
    
    # New method for diagnostic data
    def read_diagnostic_data(self) -> Optional[List[DiagnosticData]]
```

**Implementation Details**:
- Extend existing `read_mppt_data()` to also read Tmp, DCSt, and DCEvt fields
- Access diagnostic fields via `model_160.module[i].Tmp.cvalue`, `model_160.module[i].DCSt.value`, `model_160.module[i].DCEvt.value`
- Handle cases where diagnostic fields are not available (older firmware, unsupported models)
- Maintain backward compatibility with existing MPPTData structure
- Add diagnostic data as optional extension to existing data structures

**SunSpec Model 160 Diagnostic Fields**:
```python
# For each module i in model_160.module[i]:
temperature = model_160.module[i].Tmp.cvalue    # int16, scaled to Celsius
state = model_160.module[i].DCSt.value          # enum16, raw value
events = model_160.module[i].DCEvt.value        # bitfield32, raw value
```

### 2. Operating State Formatter

**Purpose**: Convert numeric operating state values to human-readable strings

**Interface**:
```python
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
```

### 3. Module Events Decoder

**Purpose**: Decode bitfield values into lists of active event names

**Interface**:
```python
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
```

### 4. Enhanced Data Models

**Purpose**: Extend existing data structures to include diagnostic information

**Enhanced Structures**:
```python
@dataclass
class DiagnosticData:
    """Diagnostic data for a single MPPT module."""
    temperature: Optional[float]  # Celsius
    operating_state: Optional[int]  # Raw enum value
    module_events: Optional[int]  # Raw bitfield value
    
    # Formatted versions for display
    formatted_state: str
    formatted_events: str

@dataclass
class MPPTModuleData:
    """Complete data for a single MPPT module including diagnostics."""
    # Existing power data
    voltage: float
    current: float
    power: float
    
    # New diagnostic data
    diagnostics: DiagnosticData

@dataclass
class EnhancedMPPTData:
    """Enhanced MPPT data including diagnostic information."""
    # Existing fields for backward compatibility
    mppt1: MPPTChannelData
    mppt2: MPPTChannelData
    total_power: float
    timestamp: datetime
    
    # New diagnostic data for all modules
    modules: List[MPPTModuleData]  # All available modules with diagnostics
```

### 5. Enhanced MQTT Publisher

**Purpose**: Extend existing MQTT publisher to handle diagnostic sensors

**New Interface Methods**:
```python
class MQTTPublisher:
    # Existing methods unchanged
    def publish_discovery(self, device_info: Dict[str, str]) -> bool
    def publish_sensor_data(self, mppt_data: MPPTData) -> bool
    
    # New methods for diagnostic sensors
    def publish_diagnostic_discovery(self, device_info: Dict[str, str], num_modules: int) -> bool
    def publish_diagnostic_data(self, diagnostic_data: List[DiagnosticData]) -> bool
```

**Diagnostic Sensor Configurations**:
```python
# Temperature sensors (disabled by default)
{
    "id": f"mppt{module_num}_temperature",
    "name": f"MPPT{module_num} Temperature", 
    "unit": "°C",
    "device_class": "temperature",
    "entity_category": "diagnostic",
    "enabled_by_default": False,
    "value_template": "{{ value_json.temperature }}"
}

# Operating state sensors (enabled by default)
{
    "id": f"mppt{module_num}_operating_state",
    "name": f"MPPT{module_num} Operating State",
    "device_class": "enum", 
    "entity_category": "diagnostic",
    "enabled_by_default": True,
    "value_template": "{{ value_json.state }}"
}

# Module events sensors (disabled by default)
{
    "id": f"mppt{module_num}_module_events", 
    "name": f"MPPT{module_num} Module Events",
    "entity_category": "diagnostic",
    "enabled_by_default": False,
    "value_template": "{{ value_json.events }}"
}
```

**MQTT Topic Structure**:
- Discovery: `{prefix}/sensor/{device_id}/mppt{N}_{diagnostic_type}/config`
- State: `{prefix}/sensor/{device_id}/mppt{N}_{diagnostic_type}/state`

**Example Topics**:
- `homeassistant/sensor/fronius_12345/mppt1_temperature/config`
- `homeassistant/sensor/fronius_12345/mppt1_temperature/state`
- `homeassistant/sensor/fronius_12345/mppt1_operating_state/config`
- `homeassistant/sensor/fronius_12345/mppt1_operating_state/state`
- `homeassistant/sensor/fronius_12345/mppt1_module_events/config`
- `homeassistant/sensor/fronius_12345/mppt1_module_events/state`

### 6. Configuration Extensions

**Purpose**: Add configuration options for diagnostic sensors

**New Configuration Options**:
```yaml
# config.yaml
diagnostic_sensors:
  enabled: true  # Global enable/disable for diagnostic sensors
  temperature:
    enabled: true
    enabled_by_default: false
  operating_state:
    enabled: true
    enabled_by_default: true
  module_events:
    enabled: true
    enabled_by_default: false
```

**Configuration Interface**:
```python
class Config:
    # Existing properties unchanged
    
    # New diagnostic sensor properties
    @property
    def diagnostic_sensors_enabled(self) -> bool
    
    @property
    def temperature_sensors_enabled(self) -> bool
    
    @property
    def temperature_sensors_default_enabled(self) -> bool
    
    @property
    def operating_state_sensors_enabled(self) -> bool
    
    @property
    def operating_state_sensors_default_enabled(self) -> bool
    
    @property
    def module_events_sensors_enabled(self) -> bool
    
    @property
    def module_events_sensors_default_enabled(self) -> bool
```

## Data Models

### SunSpec Model 160 Diagnostic Fields

**Additional Fields per Module**:
- `Tmp` (Temperature): int16, units: C, scale factor applied by pysunspec2
- `DCSt` (Operating State): enum16, no scaling (raw enum value)
- `DCEvt` (Module Events): bitfield32, no scaling (raw bitfield)

**Field Access Pattern**:
```python
# For module i
temperature = model_160.module[i].Tmp.cvalue  # Scaled temperature in Celsius
state = model_160.module[i].DCSt.value        # Raw enum value (1-10)
events = model_160.module[i].DCEvt.value      # Raw bitfield (0-4294967295)
```

### Operating State Enumeration

```python
OPERATING_STATES = {
    1: "OFF",           # Module is off
    2: "SLEEPING",      # Module is in sleep mode
    3: "STARTING",      # Module is starting up
    4: "MPPT",          # Module is in MPPT mode (normal operation)
    5: "THROTTLED",     # Module is throttled (power limited)
    6: "SHUTTING_DOWN", # Module is shutting down
    7: "FAULT",         # Module has a fault condition
    8: "STANDBY",       # Module is in standby mode
    9: "TEST",          # Module is in test mode
    10: "RESERVED_10"   # Reserved state
}
```

### Module Events Bitfield

```python
MODULE_EVENTS = {
    0: "GROUND_FAULT",        # Ground fault detected
    1: "INPUT_OVER_VOLTAGE",  # Input voltage too high
    3: "DC_DISCONNECT",       # DC disconnect open
    5: "CABINET_OPEN",        # Cabinet door open
    6: "MANUAL_SHUTDOWN",     # Manual shutdown activated
    7: "OVER_TEMP",           # Over temperature condition
    12: "BLOWN_FUSE",         # Fuse blown
    13: "UNDER_TEMP",         # Under temperature condition
    14: "MEMORY_LOSS",        # Memory loss detected
    15: "ARC_DETECTION",      # Arc fault detected
    20: "TEST_FAILED",        # Self-test failed
    21: "INPUT_UNDER_VOLTAGE", # Input voltage too low
    22: "INPUT_OVER_CURRENT"   # Input current too high
}
```

### Home Assistant Entity Categories

**Diagnostic Sensors**:
- `entity_category: "diagnostic"` - Marks sensors as diagnostic information
- `enabled_by_default: false` - Temperature and Events sensors disabled by default
- `enabled_by_default: true` - Operating State sensors enabled by default

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Diagnostic Field Extraction Completeness
*For any* SunSpec Model 160 object with N available modules, reading diagnostic data should extract Tmp, DCSt, and DCEvt fields from each module, handling cases where individual fields may be unavailable without failing the entire read operation.
**Validates: Requirements 1.1, 2.1, 3.1, 4.1**

### Property 2: Temperature Sensor Configuration
*For any* temperature sensor configuration, the generated discovery message should have device_class "temperature", unit "°C", entity_category "diagnostic", and enabled_by_default set to false.
**Validates: Requirements 1.2, 1.3**

### Property 3: Operating State Sensor Configuration  
*For any* operating state sensor configuration, the generated discovery message should have device_class "enum", entity_category "diagnostic", and enabled_by_default set to true.
**Validates: Requirements 2.2, 2.5**

### Property 4: Module Events Sensor Configuration
*For any* module events sensor configuration, the generated discovery message should have entity_category "diagnostic" and enabled_by_default set to false.
**Validates: Requirements 3.2**

### Property 5: Operating State Value Formatting
*For any* valid operating state enum value (1-10), the formatter should convert it to the correct human-readable name (OFF, SLEEPING, STARTING, MPPT, THROTTLED, SHUTTING_DOWN, FAULT, STANDBY, TEST, RESERVED_10), and for any invalid value, it should return "unknown".
**Validates: Requirements 2.3, 2.4**

### Property 6: Module Events Bitfield Decoding
*For any* module events bitfield value, the decoder should correctly identify all active events based on set bits and format them as a comma-separated list, with special handling for zero (no events) returning "No active events".
**Validates: Requirements 3.3, 3.5**

### Property 7: Data Type Handling Consistency
*For any* Model 160 diagnostic data, temperature values should be accessed via .cvalue (scaled), while operating state and module events should be accessed via .value (raw), with appropriate type conversions applied.
**Validates: Requirements 4.2**

### Property 8: Invalid Data Handling
*For any* invalid or unavailable diagnostic field value (None, out-of-range, or malformed), the system should handle it gracefully by reporting appropriate unavailable/unknown states without affecting other sensors or core functionality.
**Validates: Requirements 1.4, 2.4, 4.4, 7.1, 7.2**

### Property 9: Graceful Degradation
*For any* system state where diagnostic fields are unavailable but core MPPT data is available, the system should continue operating normally with existing functionality unaffected.
**Validates: Requirements 4.3, 7.1**

### Property 10: MQTT Discovery Message Structure
*For any* diagnostic sensor, the generated MQTT discovery message should include proper device classes, units of measurement, device information, unique identifiers, and all sensors should reference the same device identifier as existing MPPT sensors.
**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

### Property 11: Configuration-Driven Sensor Creation
*For any* diagnostic sensor configuration settings, the system should respect global enable/disable flags and create only the sensor types that are enabled in the configuration.
**Validates: Requirements 6.1**

### Property 12: Configuration Validation and Defaults
*For any* diagnostic sensor configuration (including missing sections), the parser should validate settings and provide meaningful error messages for invalid configurations, while using sensible defaults when configuration sections are missing.
**Validates: Requirements 6.3, 6.4**

### Property 13: Sensor Creation Resilience
*For any* set of diagnostic sensors being created, if individual sensor creation fails, the system should continue creating remaining sensors and log appropriate errors without terminating the entire process.
**Validates: Requirements 7.3**

<function_calls>
<invoke name="prework">
<parameter name="featureName">diagnostic-sensors

## Error Handling

### Diagnostic Data Unavailability

**Missing Diagnostic Fields**:
- If Tmp, DCSt, or DCEvt fields are not available in Model 160, log warning and continue with available fields
- Individual field unavailability should not prevent reading other diagnostic fields
- Core MPPT functionality (voltage, current, power) must remain unaffected
- Unavailable diagnostic sensors should report "unavailable" state in Home Assistant

**Invalid Field Values**:
- Temperature values outside reasonable range (-40°C to 150°C): Report as "unavailable"
- Operating state values outside enum range (1-10): Format as "unknown_{value}"
- Module events bitfield with invalid bits: Decode available bits, ignore invalid ones
- Null or None values from pysunspec2: Handle gracefully with appropriate unavailable states

### Sensor Creation Failures

**Individual Sensor Failures**:
- If temperature sensor creation fails, continue with operating state and events sensors
- If operating state sensor creation fails, continue with temperature and events sensors
- If events sensor creation fails, continue with temperature and operating state sensors
- Log specific error for each failed sensor creation
- Ensure existing MPPT sensors remain functional

**Discovery Message Failures**:
- If MQTT discovery message publication fails for diagnostic sensors, retry with exponential backoff
- Continue with data polling even if discovery messages fail
- Re-publish discovery messages when MQTT connection is re-established
- Maintain existing discovery message functionality for core MPPT sensors

### Configuration Errors

**Invalid Diagnostic Configuration**:
- Missing diagnostic_sensors section: Use default settings (all enabled, appropriate defaults)
- Invalid boolean values: Log error with specific field name, use safe defaults
- Unknown configuration keys: Log warning, ignore unknown keys
- Malformed YAML in diagnostic section: Log error, fall back to defaults

**Validation Errors**:
- Provide specific error messages identifying problematic configuration fields
- Include expected value types and valid ranges in error messages
- Exit gracefully with non-zero exit code for critical configuration errors
- Allow system to start with warnings for non-critical configuration issues

### Runtime Error Recovery

**Modbus Communication Errors**:
- If diagnostic field reads fail but core MPPT reads succeed, mark diagnostic sensors as unavailable
- If entire Model 160 read fails, apply existing exponential backoff retry logic
- Maintain separate availability states for diagnostic vs. core sensors
- Automatically recover diagnostic sensors when Modbus communication is restored

**MQTT Publishing Errors**:
- Queue diagnostic sensor updates if MQTT connection is temporarily unavailable
- Retry diagnostic data publication with same logic as core sensor data
- Ensure diagnostic sensor failures don't affect core sensor data publishing
- Re-establish diagnostic sensor states when MQTT connection is restored

## Testing Strategy

This feature will extend the existing dual testing approach (unit tests + property-based tests) to ensure comprehensive coverage of diagnostic sensor functionality.

### Unit Testing

Unit tests will focus on:
- **Specific examples**: Known diagnostic field values and expected formatted outputs
- **Edge cases**: Boundary values for temperature, invalid enum states, empty bitfields
- **Integration points**: Interaction between diagnostic and core sensor functionality
- **Error conditions**: Specific failure scenarios for diagnostic data reading

Example unit tests:
- Test operating state formatting for each valid enum value (1-10)
- Test module events decoding for specific bitfield combinations
- Test temperature sensor discovery message generation
- Test configuration parsing with missing diagnostic sections
- Test error handling when diagnostic fields return None

### Property-Based Testing

Property-based tests will verify universal properties across many generated inputs using the **Hypothesis** library for Python.

**Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with: `# Feature: diagnostic-sensors, Property N: [property text]`

**Test Coverage**:

1. **Diagnostic Field Extraction (Property 1)**
   - Generate mock Model 160 objects with random number of modules (0-4)
   - Generate random diagnostic field values (temperature: -50 to 200°C, state: 0-15, events: 0-4294967295)
   - Include cases where fields are None or unavailable
   - Verify: All available fields are extracted correctly
   - Verify: Unavailable fields are handled gracefully

2. **Sensor Configuration Generation (Properties 2, 3, 4)**
   - Generate random module numbers and sensor types
   - Verify: Discovery messages have correct device classes, units, and default states
   - Verify: All diagnostic sensors have entity_category "diagnostic"

3. **Value Formatting (Properties 5, 6)**
   - Generate random operating state values (including invalid ones)
   - Generate random module events bitfields (including edge cases)
   - Verify: Valid values format correctly, invalid values handled gracefully
   - Verify: Bitfield decoding produces correct event lists

4. **Data Type Handling (Property 7)**
   - Generate mock pysunspec2 objects with different field types
   - Verify: Temperature uses .cvalue, state/events use .value
   - Verify: Type conversions are applied correctly

5. **Error Handling (Properties 8, 9)**
   - Generate invalid diagnostic data while keeping core MPPT data valid
   - Verify: System continues operating with core functionality
   - Verify: Invalid data results in appropriate unavailable states

6. **MQTT Integration (Property 10)**
   - Generate random device information and sensor configurations
   - Verify: Discovery messages have required fields and proper structure
   - Verify: All sensors reference same device identifier

7. **Configuration Handling (Properties 11, 12)**
   - Generate random configuration combinations (enabled/disabled sensors)
   - Generate invalid configurations and missing sections
   - Verify: Configuration controls sensor creation correctly
   - Verify: Validation catches errors and provides meaningful messages

**Generator Strategies**:
- Mock pysunspec2 Model 160 objects with configurable field availability
- Temperature values: Normal range (-40 to 150°C) plus edge cases
- Operating states: Valid enum values (1-10) plus invalid values (0, 11-255)
- Module events: Random bitfields including single bits, multiple bits, and edge cases
- Configuration objects: Valid combinations plus missing sections and invalid values
- Device information: Random manufacturer, model, serial number combinations

### Integration Testing

Integration tests will verify:
- End-to-end diagnostic sensor functionality with mock Home Assistant
- Interaction between diagnostic sensors and existing MPPT sensors
- Configuration loading and sensor creation with real YAML files
- Error recovery scenarios with simulated Modbus and MQTT failures
- Docker container startup with diagnostic sensor configuration

### Test Execution

- Unit tests: Run with `pytest tests/unit/test_diagnostic_sensors.py`
- Property tests: Run with `pytest tests/property/test_diagnostic_properties.py`
- Integration tests: Run with `pytest tests/integration/test_diagnostic_integration.py`
- All tests: Run with `make test`

The existing test infrastructure will be extended to include diagnostic sensor test modules, maintaining the same quality standards and coverage requirements as the core functionality.