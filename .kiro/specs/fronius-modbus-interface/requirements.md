# Requirements Document

## Introduction

This system interfaces with Fronius Symo solar inverters using the Modbus protocol to retrieve extended Maximum Power Point Tracking (MPPT) information. The system is implemented in Python using the pysunspec2 library, polls the inverter every 5 seconds, and publishes voltage, current, and power data for PV1 and PV2 channels to Home Assistant via MQTT using the self-advertising sensor discovery pattern.

## Glossary

- **Fronius_Symo**: A series of solar inverters manufactured by Fronius that support Modbus communication
- **Modbus**: An industrial communication protocol used for device communication
- **MPPT**: Maximum Power Point Tracking - technology that optimizes solar panel power output
- **MPPT_Channel**: Individual power tracking channel within the inverter (Fronius Symo has 2 MPPT channels: PV1 and PV2)
- **Modbus_Client**: The software component that initiates communication with the inverter
- **Inverter**: The Fronius Symo device being monitored
- **Register**: A Modbus data storage location containing specific inverter information
- **MQTT**: Message Queuing Telemetry Transport - a lightweight messaging protocol for IoT devices
- **MQTT_Broker**: The server that receives and routes MQTT messages
- **Home_Assistant**: An open-source home automation platform
- **MQTT_Discovery**: Home Assistant's automatic device and sensor configuration via MQTT messages
- **Discovery_Topic**: MQTT topic used for Home Assistant auto-discovery (homeassistant/sensor/...)
- **State_Topic**: MQTT topic where sensor values are published
- **System**: The complete Fronius Modbus to MQTT bridge application
- **SunSpec**: A communication standard for solar inverters and related devices
- **Model_1**: SunSpec Common Model containing inverter identification information
- **Model_160**: SunSpec model type for Multiple MPPT Inverter Extension
- **Docker**: A containerization platform for packaging applications with their dependencies
- **Docker_Container**: A runnable instance of a Docker image
- **Docker_Compose**: A tool for defining and running multi-container Docker applications
- **Makefile**: A build automation file containing targets for common operations
- **Python**: The programming language used for implementation
- **pysunspec2**: A Python library for communicating with SunSpec-compliant devices via Modbus
- **YAML**: A human-readable data serialization format used for configuration files
- **Config_File**: A YAML configuration file containing all system parameters

## Requirements

### Requirement 1: Establish Modbus Connection

**User Story:** As a system operator, I want to establish a Modbus connection to the Fronius Symo inverter using pysunspec2, so that I can communicate with the device and retrieve data.

#### Acceptance Criteria

1. WHEN connection parameters are provided (IP address, port, unit ID), THE System SHALL use pysunspec2 to establish a TCP connection to the Inverter
2. IF the Modbus connection fails, THEN THE System SHALL log a descriptive error indicating the failure reason
3. WHEN the connection is established, THE System SHALL verify communication by performing device scan
4. THE System SHALL support configurable timeout values for connection attempts
5. IF the Modbus connection is lost or fails, THEN THE System SHALL attempt reconnection with exponential backoff
6. THE System SHALL continue attempting to connect indefinitely until successful

### Requirement 2: Verify SunSpec Model 160 Support

**User Story:** As a system operator, I want to verify the inverter supports SunSpec Model 160, so that I can ensure the correct data model is available before attempting to read MPPT data.

#### Acceptance Criteria

1. WHEN the Modbus connection is established, THE System SHALL perform device scan to discover available models
2. IF Model 160 is discovered, THEN THE System SHALL proceed with normal operation
3. IF Model 160 is not discovered, THEN THE System SHALL log an error message indicating Model 160 is not supported
4. IF Model 160 is not found, THEN THE System SHALL continue attempting to scan and discover models
5. THE System SHALL use pysunspec2's scan() method to discover models according to SunSpec specifications

### Requirement 3: Read Device Information

**User Story:** As a system operator, I want to read device identification information from the inverter, so that I can properly identify the device in Home Assistant.

#### Acceptance Criteria

1. WHEN the Modbus connection is established, THE System SHALL read SunSpec Common Model (Model 1) if available
2. WHEN Model 1 is available, THE System SHALL extract manufacturer name from the model
3. WHEN Model 1 is available, THE System SHALL extract model name from the model
4. WHEN Model 1 is available, THE System SHALL extract serial number from the model
5. THE System SHALL use extracted device information in MQTT discovery messages

### Requirement 4: Read MPPT Channel Data

**User Story:** As a solar system monitor, I want to read extended MPPT data from each channel using SunSpec Model 160 via pysunspec2, so that I can retrieve accurate voltage, current, and power measurements.

#### Acceptance Criteria

1. THE System SHALL use pysunspec2 to read SunSpec Model 160 data from the Inverter
2. WHEN Model 160 data is read, THE System SHALL extract voltage values for MPPT1 and MPPT2 using the computed value (cvalue) attribute
3. WHEN Model 160 data is read, THE System SHALL extract current values for MPPT1 and MPPT2 using the computed value (cvalue) attribute
4. WHEN Model 160 data is read, THE System SHALL extract power values for MPPT1 and MPPT2 using the computed value (cvalue) attribute
5. WHEN Model 160 data is read, THE System SHALL extract total DC power value using the computed value (cvalue) attribute
6. THE System SHALL use pysunspec2's automatic scaling factor application via the cvalue attribute

### Requirement 5: Periodic Data Polling

**User Story:** As a monitoring system, I want to automatically poll MPPT data at regular intervals, so that I can track inverter performance continuously without manual intervention.

#### Acceptance Criteria

1. THE System SHALL poll MPPT data every 5 seconds by default
2. THE System SHALL continue polling until explicitly stopped
3. WHEN a polling cycle completes, THE System SHALL wait for the configured interval before the next poll
4. IF a polling operation fails, THE System SHALL continue polling on the next scheduled interval
5. THE System SHALL support configurable polling intervals

### Requirement 5: Periodic Data Polling

**User Story:** As a monitoring system, I want to automatically poll MPPT data at regular intervals, so that I can track inverter performance continuously without manual intervention.

#### Acceptance Criteria

1. THE System SHALL poll MPPT data every 5 seconds by default
2. THE System SHALL continue polling until explicitly stopped
3. WHEN a polling cycle completes, THE System SHALL wait for the configured interval before the next poll
4. IF a polling operation fails, THE System SHALL continue polling on the next scheduled interval
5. THE System SHALL support configurable polling intervals

### Requirement 6: Establish MQTT Connection

**User Story:** As a system operator, I want to establish an MQTT connection to my broker, so that I can publish inverter data to Home Assistant.

#### Acceptance Criteria

1. WHEN MQTT connection parameters are provided (broker address, port, username, password), THE System SHALL establish a connection to the MQTT_Broker
2. IF the MQTT connection fails, THEN THE System SHALL log a descriptive error indicating the failure reason
3. THE System SHALL support configurable MQTT broker address, port, username, password, and client ID
4. IF the MQTT connection is lost or fails, THEN THE System SHALL attempt reconnection with exponential backoff
5. WHEN the MQTT connection is re-established, THE System SHALL republish discovery messages
6. THE System SHALL continue attempting to connect indefinitely until successful

### Requirement 7: Establish MQTT Connection

**User Story:** As a system operator, I want to establish an MQTT connection to my broker, so that I can publish inverter data to Home Assistant.

#### Acceptance Criteria

1. WHEN MQTT connection parameters are provided (broker address, port, username, password), THE System SHALL establish a connection to the MQTT_Broker
2. IF the MQTT connection fails, THEN THE System SHALL log a descriptive error indicating the failure reason
3. THE System SHALL support configurable MQTT broker address, port, username, password, and client ID
4. IF the MQTT connection is lost or fails, THEN THE System SHALL attempt reconnection with exponential backoff
5. WHEN the MQTT connection is re-established, THE System SHALL republish discovery messages
6. THE System SHALL continue attempting to connect indefinitely until successful

### Requirement 8: MQTT Publishing

**User Story:** As a Home Assistant user, I want MPPT data published to MQTT, so that I can monitor my solar inverter in my home automation system.

#### Acceptance Criteria

1. WHEN MPPT data is successfully read, THE System SHALL publish the data to MQTT
2. THE System SHALL publish voltage, current, and power values for MPPT1 to separate MQTT state topics
3. THE System SHALL publish voltage, current, and power values for MPPT2 to separate MQTT state topics
4. THE System SHALL publish total PV power to a separate MQTT state topic
5. WHEN MQTT publishing fails, THE System SHALL continue polling Modbus data and retry MQTT publishing on the next cycle
6. THE System SHALL publish numeric values in the MQTT payload
7. THE System SHALL include timestamp information with each published reading

### Requirement 8: MQTT Publishing

**User Story:** As a Home Assistant user, I want MPPT data published to MQTT, so that I can monitor my solar inverter in my home automation system.

#### Acceptance Criteria

1. WHEN MPPT data is successfully read, THE System SHALL publish the data to MQTT
2. THE System SHALL publish voltage, current, and power values for MPPT1 to separate MQTT state topics
3. THE System SHALL publish voltage, current, and power values for MPPT2 to separate MQTT state topics
4. THE System SHALL publish total DC power to a separate MQTT state topic
5. WHEN MQTT publishing fails, THE System SHALL continue polling Modbus data and retry MQTT publishing on the next cycle
6. THE System SHALL publish numeric values in the MQTT payload
7. THE System SHALL include timestamp information with each published reading

### Requirement 9: Home Assistant MQTT Discovery

**User Story:** As a Home Assistant user, I want sensors to be automatically discovered, so that I don't have to manually configure each sensor in Home Assistant.

#### Acceptance Criteria

1. WHEN the System starts and MQTT connection is established, THE System SHALL publish MQTT discovery messages for all MPPT sensors
2. THE System SHALL publish discovery messages following the Home Assistant MQTT Discovery format
3. THE System SHALL create discovery configurations for MPPT1 voltage, current, and power sensors
4. THE System SHALL create discovery configurations for MPPT2 voltage, current, and power sensors
5. THE System SHALL include appropriate device class, unit of measurement, state class, and unique IDs in discovery messages
6. THE System SHALL set state_class to "measurement" for all sensor discovery messages
7. THE System SHALL publish discovery messages to topics following the pattern: homeassistant/sensor/{device_id}/{sensor_id}/config
8. WHEN discovery messages are published, THE System SHALL include device information grouping all sensors under the Fronius inverter device
9. THE System SHALL read inverter manufacturer, model, and serial number from pysunspec2 and include them in device information
10. THE System SHALL use device information from SunSpec Common Model (Model 1) if available

### Requirement 9: Handle Communication Errors

**User Story:** As a system operator, I want the system to handle communication errors gracefully, so that temporary network issues don't crash the monitoring system.

#### Acceptance Criteria

1. WHEN a Modbus read operation times out, THE System SHALL log the error and continue operation without crashing
2. WHEN invalid Modbus data is received, THE System SHALL validate the response and log an error for invalid data
3. WHEN Modbus communication errors occur, THE System SHALL log the error details for troubleshooting
4. WHEN MQTT publishing fails, THE System SHALL log the error and continue polling
5. THE System SHALL distinguish between temporary network errors and configuration errors
6. WHEN either Modbus or MQTT connections fail, THE System SHALL continue attempting to operate with available connections

### Requirement 10: Configuration Management

**User Story:** As a system administrator, I want to configure all system parameters via a YAML configuration file, so that I can easily manage connection settings, logging levels, and polling rates without modifying code.

#### Acceptance Criteria

1. THE System SHALL read all configuration parameters from a YAML Config_File
2. THE Config_File SHALL be located in the same directory as the main executable by default
3. THE System SHALL support a --config command-line argument to specify an alternate Config_File location
4. THE Config_File SHALL contain Modbus connection parameters (IP address, port, unit ID, timeout)
5. THE Config_File SHALL contain MQTT connection parameters (broker address, port, username, password, client ID, topic prefix)
6. THE Config_File SHALL contain logging configuration (log level, log format)
7. THE Config_File SHALL contain polling interval configuration
8. THE Config_File SHALL contain MQTT republish rate configuration
9. THE System SHALL validate all configuration parameters before attempting connections
10. WHERE configuration is invalid, THE System SHALL provide clear error messages indicating which parameters are incorrect

### Requirement 11: Logging

**User Story:** As a system operator, I want configurable logging, so that I can troubleshoot issues and monitor system behavior at appropriate detail levels.

#### Acceptance Criteria

1. THE System SHALL implement logging for all major operations and errors
2. THE System SHALL support configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
3. THE System SHALL read log level configuration from the Config_File
4. WHEN logging to stdout, THE System SHALL use a consistent log format with timestamps
5. THE System SHALL log Modbus connection events (connect, disconnect, errors)
6. THE System SHALL log MQTT connection events (connect, disconnect, errors)
7. THE System SHALL log data polling operations at appropriate log levels
8. THE System SHALL log configuration validation results

### Requirement 12: Docker Containerization

**User Story:** As a system administrator, I want the application packaged as a Docker container, so that I can deploy it consistently across different environments without dependency issues.

#### Acceptance Criteria

1. THE System SHALL provide a Dockerfile that builds a runnable Docker_Container
2. THE Docker_Container SHALL include all necessary dependencies to run the application
3. THE Docker_Container SHALL accept configuration via a mounted config file at /etc/fronius-mppt-bridge/config.yaml
4. THE Docker_Container SHALL run the application with --config /etc/fronius-mppt-bridge/config.yaml argument
5. THE Docker_Container SHALL run the application as a non-root user for security
6. WHEN the Docker_Container starts, THE System SHALL begin attempting to connect and poll data
7. THE Docker_Container SHALL log output to stdout for container log collection

### Requirement 13: Docker Multi-Architecture Support

**User Story:** As a deployment engineer, I want Docker images built for multiple architectures (Intel x64 and ARM), so that I can deploy the system on different hardware platforms including Raspberry Pi and x86 servers.

#### Acceptance Criteria

1. THE System SHALL provide Docker images built for both linux/amd64 and linux/arm64 architectures
2. THE System SHALL use Docker buildx for multi-platform image creation
3. THE System SHALL provide a Makefile target to build multi-architecture images
4. THE System SHALL provide a Makefile target to push images to a configurable Docker registry
5. THE Docker registry target SHALL be configurable via DOCKER_USER environment variable
6. THE System SHALL tag images with both 'latest' and version-specific tags
7. THE multi-architecture images SHALL be pushed as a single manifest supporting both platforms

### Requirement 14: Docker Compose and Build Automation

**User Story:** As a developer, I want a Makefile with docker-compose integration, so that I can easily build, run, and manage the containerized application.

#### Acceptance Criteria

1. THE System SHALL provide a docker-compose.yml file for container orchestration
2. THE docker-compose.yml SHALL mount a local config file to /etc/fronius-mppt-bridge/config.yaml in the container
3. THE System SHALL provide a Makefile with targets for common operations
4. THE Makefile SHALL include a target to build the Docker image
5. THE Makefile SHALL include a target to start the application using docker-compose
6. THE Makefile SHALL include a target to stop the application using docker-compose
7. THE Makefile SHALL include a target to view application logs
8. THE docker-compose.yml SHALL support configuration via a local config.yaml file
