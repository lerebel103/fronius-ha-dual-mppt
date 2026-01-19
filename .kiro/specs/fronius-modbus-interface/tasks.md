# Implementation Plan: Fronius Modbus Interface

## Overview

This implementation plan breaks down the Fronius Modbus to MQTT bridge into discrete, testable tasks. The system uses pysunspec2 to read MPPT data from Fronius Symo inverters and publishes it to Home Assistant via MQTT with auto-discovery.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create Python project structure with src/ and tests/ directories
  - Create requirements.txt with pysunspec2, paho-mqtt, PyYAML, hypothesis
  - Create requirements-dev.txt with pytest, black, flake8, mypy, isort
  - Create setup.py or pyproject.toml for package configuration
  - Set up logging configuration
  - Create .flake8 configuration file
  - Create pyproject.toml with black and isort configuration
  - _Requirements: 10.1, 11.1, 11.2, 11.3, 11.4_

- [x] 2. Implement configuration management
  - [x] 2.1 Create Config class to load and parse YAML configuration
    - Implement __init__ to load config from file path
    - Parse Modbus, MQTT, and application sections
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [x] 2.2 Implement configuration validation
    - Validate all required fields are present
    - Validate data types and value ranges
    - Return descriptive error messages for invalid config
    - _Requirements: 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 10.10_
  
  - [ ]* 2.3 Write property test for configuration parsing
    - **Property 13: Configuration Parsing**
    - **Validates: Requirements 10.1**
  
  - [ ]* 2.4 Write property test for configuration validation
    - **Property 14: Configuration Validation**
    - **Validates: Requirements 10.4, 10.5, 10.6, 10.7, 10.8, 10.9**
  
  - [ ]* 2.5 Write property test for invalid configuration error messages
    - **Property 15: Invalid Configuration Error Messages**
    - **Validates: Requirements 10.10**

- [x] 3. Implement Modbus client with pysunspec2
  - [x] 3.1 Create ModbusClient class
    - Initialize with host, port, unit_id, timeout
    - Create pysunspec2 SunSpecModbusClientDeviceTCP instance
    - _Requirements: 1.1_
  
  - [x] 3.2 Implement connect() method with error handling
    - Attempt connection and device scan
    - Log connection success/failure
    - Return boolean indicating success
    - _Requirements: 1.1, 1.2, 1.3, 1.6_
  
  - [x] 3.3 Implement verify_model_160() method
    - Check if Model 160 exists in device.models
    - Log result
    - Return boolean
    - _Requirements: 2.1, 2.2, 2.3, 2.5_
  
  - [x] 3.4 Implement read_device_info() method
    - Read Model 1 (Common Model) if available
    - Extract manufacturer, model, serial number using .cvalue
    - Return device info dictionary
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [x] 3.5 Implement read_mppt_data() method
    - Read Model 160 data
    - Extract voltage, current, power for MPPT1 and MPPT2 using .cvalue
    - Calculate total PV power
    - Return MPPTData object with timestamp
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  
  - [ ]* 3.6 Write property test for MPPT data extraction
    - **Property 1: MPPT Data Extraction**
    - **Validates: Requirements 4.2, 4.3, 4.4**
  
  - [ ]* 3.7 Write property test for device information extraction
    - **Property 7: Device Information from Model 1**
    - **Validates: Requirements 3.2, 3.3, 3.4**
  
  - [ ]* 3.8 Write unit tests for connection error handling
    - Test connection failure scenarios
    - Test Model 160 not found scenario
    - _Requirements: 1.2, 2.3, 2.4_

- [x] 4. Implement MQTT publisher
  - [x] 4.1 Create MQTTPublisher class
    - Initialize with broker, port, username, password, client_id, topic_prefix
    - Create paho-mqtt client instance
    - _Requirements: 6.1, 6.3_
  
  - [x] 4.2 Implement connect() method
    - Attempt MQTT connection
    - Log connection success/failure
    - Return boolean indicating success
    - _Requirements: 6.1, 6.2, 6.6_
  
  - [x] 4.3 Implement publish_discovery() method
    - Generate discovery messages for all 7 sensors (MPPT1/2 voltage, current, power + total power)
    - Include state_class: "measurement"
    - Include device information from Model 1
    - Publish to discovery topics
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10_
  
  - [x] 4.4 Implement publish_sensor_data() method
    - Format MPPT data as JSON payloads
    - Publish to state topics for each sensor
    - Include timestamp
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_
  
  - [ ]* 4.5 Write property test for MQTT topic structure
    - **Property 2: MQTT Topic Structure**
    - **Validates: Requirements 7.2, 7.3**
  
  - [ ]* 4.6 Write property test for MQTT payload numeric values
    - **Property 3: MQTT Payload Contains Numeric Values**
    - **Validates: Requirements 7.6**
  
  - [ ]* 4.7 Write property test for MQTT payload timestamp
    - **Property 4: MQTT Payload Contains Timestamp**
    - **Validates: Requirements 7.7**
  
  - [ ]* 4.8 Write property test for discovery message format
    - **Property 5: Home Assistant Discovery Format**
    - **Validates: Requirements 8.2, 8.5, 8.6**
  
  - [ ]* 4.9 Write property test for discovery state class
    - **Property 6: Discovery State Class**
    - **Validates: Requirements 8.6**
  
  - [ ]* 4.10 Write property test for discovery message count
    - **Property 8: Discovery Messages for All Sensors**
    - **Validates: Requirements 8.3, 8.4**
  
  - [ ]* 4.11 Write property test for discovery topic pattern
    - **Property 9: Discovery Topic Pattern**
    - **Validates: Requirements 8.7**
  
  - [ ]* 4.12 Write property test for device grouping
    - **Property 10: Device Grouping in Discovery**
    - **Validates: Requirements 8.8**

- [x] 5. Implement main application loop
  - [x] 5.1 Create main() function with argument parsing
    - Parse --config command-line argument
    - Default to config.yaml in same directory
    - _Requirements: 10.2, 10.3_
  
  - [x] 5.2 Implement resilient connection handling
    - Initialize connection state flags
    - Attempt Modbus connection in loop
    - Attempt MQTT connection in loop
    - Implement exponential backoff for retries
    - _Requirements: 1.5, 1.6, 6.4, 6.6_
  
  - [x] 5.3 Implement polling loop
    - Poll MPPT data when connected
    - Publish to MQTT when both connections available
    - Handle errors gracefully without crashing
    - Sleep for configured interval
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_
  
  - [x] 5.4 Fix polling time drift in main loop
    - Implement absolute time reference tracking
    - Calculate accurate sleep time to prevent drift
    - Maintain consistent polling intervals regardless of processing time
    - Handle cases where processing takes longer than poll interval
    - _Requirements: 5.1, 5.2_
  
  - [ ]* 5.5 Write unit tests for main loop error handling
    - Test behavior when Modbus fails
    - Test behavior when MQTT fails
    - Test behavior when both fail
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.6_

- [x] 6. Checkpoint - Ensure core functionality works
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Create Docker configuration
  - [x] 7.1 Create Dockerfile
    - Use Python base image
    - Install dependencies
    - Copy application code
    - Create non-root user
    - Set CMD to run with --config /etc/fronius-ha-dual-mppt/config.yaml
    - _Requirements: 12.1, 12.2, 12.4, 12.5_
  
  - [x] 7.2 Create docker-compose.yml
    - Define service configuration
    - Mount local config.yaml to /etc/fronius-ha-dual-mppt/config.yaml
    - Configure logging to stdout
    - _Requirements: 13.1, 13.2, 13.8_
  
  - [x] 7.3 Create example config.yaml
    - Include all required parameters with example values
    - Add comments explaining each section
    - _Requirements: 10.4, 10.5, 10.6, 10.7, 10.8_

- [x] 8. Create Makefile for build automation
  - [x] 8.1 Add build target
    - Build Docker image
    - _Requirements: 13.3, 13.4_
  
  - [x] 8.2 Add up/start target
    - Start application with docker-compose
    - _Requirements: 13.5_
  
  - [x] 8.3 Add down/stop target
    - Stop application with docker-compose
    - _Requirements: 13.6_
  
  - [x] 8.4 Add logs target
    - View application logs
    - _Requirements: 13.7_
  
  - [x] 8.5 Add test target
    - Run all tests (unit and property)
    - _Requirements: Testing Strategy_
  
  - [x] 8.6 Add lint target
    - Run flake8 for linting
    - Run black --check for formatting
    - Run isort --check for import sorting
    - Run mypy for type checking
  
  - [x] 8.7 Add format target
    - Run black for code formatting
    - Run isort for import sorting

- [x] 9. Create README documentation
  - Document configuration file format
  - Document Docker deployment steps
  - Document Makefile targets
  - Include example Home Assistant configuration
  - Document SunSpec Model 160 requirements

- [x] 10. Final checkpoint - Integration testing
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Add sensor expiration support
  - [x] 11.1 Add expire_after parameter to MQTT discovery messages
    - Add "expire_after": 3600 to all sensor discovery payloads
    - Ensure sensors become unavailable after 1 hour without data
    - _Requirements: Home Assistant sensor availability management_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The system is designed to be resilient - it never exits due to connection failures
- pysunspec2 handles all Modbus communication and scaling automatically
