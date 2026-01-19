# Requirements Document

## Introduction

This feature adds missing diagnostic sensors from SunSpec Model 160 to provide comprehensive monitoring of MPPT module health and operational status. The implementation will expose Temperature, Operating State, and Module Events as diagnostic sensors in Home Assistant, with appropriate default visibility settings to balance information availability with user interface clarity.

## Glossary

- **MPPT_Module**: Maximum Power Point Tracking module within a solar inverter
- **Diagnostic_Sensor**: Home Assistant sensor entity that provides diagnostic information, typically disabled by default
- **SunSpec_Model_160**: Industry standard specification for DC module-level monitoring data
- **Operating_State**: Current operational mode of an MPPT module (OFF, SLEEPING, STARTING, etc.)
- **Module_Events**: Bitfield containing active fault and status conditions for an MPPT module
- **Temperature_Sensor**: Sensor measuring module temperature in Celsius
- **Home_Assistant**: Open-source home automation platform
- **Device_Class**: Home Assistant classification that determines sensor icon and behavior
- **Entity_Registry**: Home Assistant system for managing sensor entities and their enabled/disabled state

## Requirements

### Requirement 1: Temperature Sensor Implementation

**User Story:** As a solar system owner, I want to monitor MPPT module temperatures, so that I can detect overheating conditions and optimize system performance.

#### Acceptance Criteria

1. WHEN the system reads SunSpec Model 160 data, THE Temperature_Reader SHALL extract the Tmp field for each MPPT_Module
2. WHEN creating temperature sensors, THE Sensor_Factory SHALL create diagnostic sensors with device class "temperature" and unit "°C"
3. WHEN temperature sensors are first discovered, THE Home_Assistant SHALL register them as disabled by default
4. WHEN a temperature value is invalid or unavailable, THE Temperature_Sensor SHALL report "unavailable" state
5. THE Temperature_Sensor SHALL update values according to the configured polling interval

### Requirement 2: Operating State Sensor Implementation

**User Story:** As a solar system owner, I want to see the current operating state of each MPPT module, so that I can understand system behavior and identify operational issues.

#### Acceptance Criteria

1. WHEN the system reads SunSpec Model 160 data, THE State_Reader SHALL extract the DCSt field for each MPPT_Module
2. WHEN creating operating state sensors, THE Sensor_Factory SHALL create diagnostic sensors enabled by default
3. WHEN displaying operating states, THE State_Formatter SHALL convert numeric values to human-readable names (OFF, SLEEPING, STARTING, MPPT, THROTTLED, SHUTTING_DOWN, FAULT, STANDBY, TEST, RESERVED_10)
4. WHEN an operating state value is invalid, THE Operating_State_Sensor SHALL report "unknown" state
5. THE Operating_State_Sensor SHALL use device class "enum" for proper Home Assistant integration

### Requirement 3: Module Events Sensor Implementation

**User Story:** As a solar system owner, I want to see active fault and event conditions for each MPPT module, so that I can quickly identify and address system problems.

#### Acceptance Criteria

1. WHEN the system reads SunSpec Model 160 data, THE Event_Reader SHALL extract the DCEvt bitfield for each MPPT_Module
2. WHEN creating module event sensors, THE Sensor_Factory SHALL create diagnostic sensors disabled by default
3. WHEN processing module events, THE Event_Decoder SHALL decode the bitfield into active event names (GROUND_FAULT, INPUT_OVER_VOLTAGE, DC_DISCONNECT, CABINET_OPEN, MANUAL_SHUTDOWN, OVER_TEMP, BLOWN_FUSE, UNDER_TEMP, MEMORY_LOSS, ARC_DETECTION, TEST_FAILED, INPUT_UNDER_VOLTAGE, INPUT_OVER_CURRENT)
4. WHEN no events are active, THE Module_Events_Sensor SHALL display "No active events"
5. WHEN multiple events are active, THE Module_Events_Sensor SHALL display them as a comma-separated list

### Requirement 4: Data Integration and Parsing

**User Story:** As a system integrator, I want the diagnostic sensors to seamlessly integrate with existing SunSpec Model 160 data reading, so that performance impact is minimized.

#### Acceptance Criteria

1. WHEN reading Model 160 data, THE Modbus_Client SHALL retrieve Tmp, DCSt, and DCEvt fields in addition to existing fields
2. WHEN parsing Model 160 responses, THE Data_Parser SHALL handle all three new fields with appropriate data type conversions
3. WHEN Model 160 data is unavailable, THE System SHALL continue operating with existing functionality unaffected
4. THE Data_Parser SHALL validate field values against SunSpec specifications before processing
5. WHEN encountering parsing errors, THE System SHALL log errors and continue with available data

### Requirement 5: Home Assistant Integration

**User Story:** As a Home Assistant user, I want diagnostic sensors to follow Home Assistant conventions, so that they integrate seamlessly with my automation platform.

#### Acceptance Criteria

1. WHEN registering sensors with Home Assistant, THE MQTT_Publisher SHALL use proper device classes and units of measurement
2. WHEN sensors are first discovered, THE System SHALL set appropriate default enabled/disabled states per sensor type
3. WHEN publishing sensor data, THE MQTT_Publisher SHALL include device information and unique identifiers
4. THE System SHALL group all diagnostic sensors under the same device as existing MPPT sensors
5. WHEN sensor states change, THE System SHALL publish updates immediately via MQTT

### Requirement 6: Configuration and Extensibility

**User Story:** As a system administrator, I want to configure diagnostic sensor behavior, so that I can customize the system for different deployment scenarios.

#### Acceptance Criteria

1. WHERE diagnostic sensor configuration is provided, THE System SHALL allow enabling/disabling sensor types globally
2. WHEN configuration specifies custom polling intervals, THE System SHALL apply them to diagnostic sensors
3. THE Configuration_Parser SHALL validate diagnostic sensor settings and provide meaningful error messages
4. WHERE no diagnostic configuration is provided, THE System SHALL use sensible defaults
5. THE System SHALL support future addition of new diagnostic sensors without breaking existing functionality

### Requirement 7: Error Handling and Resilience

**User Story:** As a system operator, I want diagnostic sensors to handle errors gracefully, so that system reliability is maintained even when diagnostic data is unavailable.

#### Acceptance Criteria

1. WHEN Modbus communication fails, THE System SHALL mark diagnostic sensors as unavailable without affecting core functionality
2. WHEN invalid data is received, THE Data_Validator SHALL reject it and maintain previous valid states
3. IF diagnostic sensor creation fails, THE System SHALL log the error and continue with remaining sensors
4. WHEN Home Assistant is unavailable, THE System SHALL queue diagnostic updates and retry publication
5. THE System SHALL recover automatically when diagnostic data becomes available again

### Requirement 8: Testing and Validation

**User Story:** As a developer, I want comprehensive tests for diagnostic sensors, so that I can ensure reliability and prevent regressions.

#### Acceptance Criteria

1. THE Test_Suite SHALL include property-based tests for data parsing and sensor creation
2. THE Test_Suite SHALL validate correct handling of all Operating State enum values
3. THE Test_Suite SHALL verify proper decoding of Module Events bitfield combinations
4. THE Test_Suite SHALL test error conditions and edge cases for all diagnostic sensors
5. THE Integration_Tests SHALL verify end-to-end functionality with mock Home Assistant instances