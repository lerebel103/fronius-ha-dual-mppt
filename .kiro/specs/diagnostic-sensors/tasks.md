# Implementation Plan: Diagnostic Sensors

## Overview

This implementation plan adds diagnostic sensors for Temperature, Operating State, and Module Events from SunSpec Model 160 to the existing Fronius Modbus interface. The approach extends the current architecture with minimal changes to core functionality, ensuring backward compatibility while providing comprehensive diagnostic capabilities.

## Tasks

- [ ] 1. Create diagnostic data structures and formatters
  - [x] 1.1 Create DiagnosticData dataclass for module diagnostic information
    - Add DiagnosticData class with temperature, operating_state, module_events fields
    - Include formatted versions for display (formatted_state, formatted_events)
    - _Requirements: 1.1, 2.1, 3.1_
  
  - [x] 1.2 Implement OperatingStateFormatter class
    - Create STATE_NAMES mapping for enum values 1-10 to human-readable names
    - Implement format_state method with proper error handling for invalid values
    - _Requirements: 2.3, 2.4_
  
  - [ ]* 1.3 Write property test for operating state formatting
    - **Property 5: Operating State Value Formatting**
    - **Validates: Requirements 2.3, 2.4**
  
  - [x] 1.4 Implement ModuleEventsDecoder class
    - Create EVENT_NAMES mapping for bitfield positions to event names
    - Implement decode_events method with bitfield parsing and comma-separated formatting
    - Handle special cases: zero bitfield returns "No active events"
    - _Requirements: 3.3, 3.4, 3.5_
  
  - [ ]* 1.5 Write property test for module events decoding
    - **Property 6: Module Events Bitfield Decoding**
    - **Validates: Requirements 3.3, 3.5**

- [ ] 2. Extend ModbusClient for diagnostic data reading
  - [x] 2.1 Add diagnostic field reading to ModbusClient
    - Extend read_mppt_data method to also read Tmp, DCSt, DCEvt fields
    - Use .cvalue for temperature (scaled), .value for state/events (raw)
    - Handle cases where diagnostic fields are unavailable
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 4.2_
  
  - [ ]* 2.2 Write property test for diagnostic field extraction
    - **Property 1: Diagnostic Field Extraction Completeness**
    - **Validates: Requirements 1.1, 2.1, 3.1, 4.1**
  
  - [ ]* 2.3 Write property test for data type handling
    - **Property 7: Data Type Handling Consistency**
    - **Validates: Requirements 4.2**
  
  - [x] 2.4 Add enhanced data structures to support diagnostics
    - Create MPPTModuleData class combining power and diagnostic data
    - Extend MPPTData to include list of all modules with diagnostics
    - Maintain backward compatibility with existing mppt1/mppt2 structure
    - _Requirements: 4.1, 4.2_

- [ ] 3. Checkpoint - Ensure diagnostic data reading works
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Extend configuration system for diagnostic sensors
  - [x] 4.1 Add diagnostic sensor configuration options
    - Extend Config class with diagnostic sensor properties
    - Add configuration validation for diagnostic sensor settings
    - Implement sensible defaults when configuration sections are missing
    - _Requirements: 6.1, 6.3, 6.4_
  
  - [ ]* 4.2 Write property test for configuration handling
    - **Property 11: Configuration-Driven Sensor Creation**
    - **Validates: Requirements 6.1**
  
  - [ ]* 4.3 Write property test for configuration validation
    - **Property 12: Configuration Validation and Defaults**
    - **Validates: Requirements 6.3, 6.4**
  
  - [x] 4.4 Update example configuration file
    - Add diagnostic_sensors section to config.example.yaml
    - Document all available diagnostic sensor options
    - _Requirements: 6.1, 6.4_

- [ ] 5. Extend MQTT Publisher for diagnostic sensors
  - [x] 5.1 Add diagnostic sensor discovery message generation
    - Create discovery message templates for temperature, operating state, and module events sensors
    - Set appropriate device classes, units, and entity categories
    - Configure enabled_by_default settings per sensor type
    - _Requirements: 1.2, 1.3, 2.2, 2.5, 3.2, 5.1, 5.2_
  
  - [ ]* 5.2 Write property test for temperature sensor configuration
    - **Property 2: Temperature Sensor Configuration**
    - **Validates: Requirements 1.2, 1.3**
  
  - [ ]* 5.3 Write property test for operating state sensor configuration
    - **Property 3: Operating State Sensor Configuration**
    - **Validates: Requirements 2.2, 2.5**
  
  - [ ]* 5.4 Write property test for module events sensor configuration
    - **Property 4: Module Events Sensor Configuration**
    - **Validates: Requirements 3.2**
  
  - [x] 5.5 Add diagnostic data publishing functionality
    - Implement publish_diagnostic_data method for sensor state updates
    - Format diagnostic data appropriately for each sensor type
    - Handle unavailable data with proper "unavailable" states
    - _Requirements: 1.4, 2.4, 5.3, 5.4_
  
  - [ ]* 5.6 Write property test for MQTT discovery message structure
    - **Property 10: MQTT Discovery Message Structure**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

- [ ] 6. Implement error handling and resilience
  - [x] 6.1 Add graceful degradation for unavailable diagnostic data
    - Ensure core MPPT functionality continues when diagnostic fields fail
    - Handle individual diagnostic field failures without affecting others
    - Implement proper logging for diagnostic data issues
    - _Requirements: 4.3, 7.1, 7.2_
  
  - [ ]* 6.2 Write property test for invalid data handling
    - **Property 8: Invalid Data Handling**
    - **Validates: Requirements 1.4, 2.4, 4.4, 7.1, 7.2**
  
  - [ ]* 6.3 Write property test for graceful degradation
    - **Property 9: Graceful Degradation**
    - **Validates: Requirements 4.3, 7.1**
  
  - [x] 6.4 Add resilient sensor creation
    - Implement error handling for individual sensor creation failures
    - Continue creating remaining sensors when individual sensors fail
    - Log specific errors for failed sensor creation attempts
    - _Requirements: 7.3_
  
  - [ ]* 6.5 Write property test for sensor creation resilience
    - **Property 13: Sensor Creation Resilience**
    - **Validates: Requirements 7.3**

- [ ] 7. Integrate diagnostic sensors into main application flow
  - [x] 7.1 Update controller to handle diagnostic sensors
    - Modify FroniusBridgeController to publish diagnostic discovery messages
    - Integrate diagnostic data publishing into main polling loop
    - Ensure diagnostic sensor failures don't affect core functionality
    - _Requirements: 5.5, 7.1_
  
  - [x] 7.2 Update main application entry point
    - Ensure diagnostic sensors are initialized when application starts
    - Handle configuration loading for diagnostic sensor settings
    - _Requirements: 6.1, 6.4_
  
  - [ ]* 7.3 Write integration tests for diagnostic sensors
    - Test end-to-end diagnostic sensor functionality
    - Verify interaction with existing MPPT sensors
    - Test configuration loading and sensor creation
    - _Requirements: 8.5_

- [ ] 8. Final checkpoint - Ensure all functionality works together
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Update documentation and examples
  - [x] 9.1 Update README with diagnostic sensor information
    - Document new diagnostic sensor capabilities
    - Explain configuration options for diagnostic sensors
    - Provide examples of diagnostic sensor usage in Home Assistant
    - _Requirements: 6.1, 6.4_
  
  - [x] 9.2 Update Docker configuration if needed
    - Ensure diagnostic sensor configuration works in containerized environment
    - Update environment variable documentation if applicable
    - _Requirements: 6.1_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation maintains backward compatibility with existing functionality
- Diagnostic sensors are designed to fail gracefully without affecting core MPPT monitoring