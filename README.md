# Fronius HA Dual MPPT

Sends solar inverter DC data to Home Assistant via MQTT, for both solar arrays. This application reads extended MPPT (Maximum Power Point Tracking) data from the inverter using the Modbus protocol and publishes it to an MQTT broker with Home Assistant auto-discovery support. Although the native Fronius integration in Home Assistant works well, it doesn't seem to report this extended data offered by inverters that support the Sunspec API, with model 160 extension as is the case for Fronius Symo.

![Dual MPPT Data in Home Assistant](./media/Dual%20MMPT%20Data%20in%20HA.png)

*Example of dual MPPT data displayed in Home Assistant showing individual string voltages, currents, and power readings*

## Installation

### Docker Hub Installation (Recommended)

Pull the pre-built image from Docker Hub:

```bash
docker pull lerebel103/fronius-ha-dual-mppt:latest
```

Then use it in your docker-compose.yml or run directly:

```bash
docker run -d \
  --name fronius-ha-dual-mppt \
  --network host \
  -v ./config.yaml:/etc/fronius-mppt-bridge/config.yaml:ro \
  --restart unless-stopped \
  lerebel103/fronius-ha-dual-mppt:latest
```

## Features

- **SunSpec Model 160 Support**: Reads detailed MPPT data from Fronius Symo inverters
- **Diagnostic Sensors**: Temperature, operating state, and module events monitoring for each MPPT channel
- **Home Assistant Integration**: Automatic sensor discovery via MQTT with proper diagnostic entity categories
- **Resilient Operation**: Automatic reconnection handling for both Modbus and MQTT
- **Docker Support**: Containerized deployment with docker-compose
- **Comprehensive Monitoring**: Voltage, current, and power data for both MPPT channels
- **Configurable Polling**: Adjustable polling intervals with drift prevention
- **Robust Error Handling**: Exponential backoff and graceful error recovery

## Requirements

### Hardware Requirements
- Fronius Symo solar inverter with Modbus TCP support
- Network connectivity between the bridge and inverter
- MQTT broker (typically Home Assistant)

### Software Requirements
- Python 3.9+ (for development)
- Docker and docker-compose (for deployment)
- Fronius inverter must support SunSpec Model 160 (Multiple MPPT Inverter Extension)

## Quick Start with Docker

1. **Clone and configure**:
   ```bash
   git clone <repository-url>
   cd fronius-ha-dual-mppt
   cp config.example.yaml config.yaml
   ```

2. **Edit configuration**:
   ```bash
   nano config.yaml
   ```
   Update the following key settings:
   - `modbus.host`: IP address of your Fronius inverter
   - `mqtt.broker`: IP address of your MQTT broker/Home Assistant
   - `mqtt.username` and `mqtt.password`: MQTT credentials

3. **Build and start**:
   ```bash
   make build
   make up
   ```

4. **View logs**:
   ```bash
   make logs
   ```

5. **Stop the service**:
   ```bash
   make down
   ```

## Configuration

### Configuration File Format

The application uses a YAML configuration file with four main sections:

```yaml
modbus:
  host: "192.168.1.100"      # Fronius inverter IP address
  port: 502                   # Modbus TCP port (standard: 502)
  unit_id: 1                  # Modbus unit ID (usually 1)
  timeout: 10                 # Connection timeout in seconds

mqtt:
  broker: "192.168.1.50"      # MQTT broker IP address (your HA server or broker)
  port: 1883                  # MQTT port (1883 unencrypted, 8883 TLS)
  username: "fronius_bridge"  # MQTT username (created in broker setup)
  password: "your_mqtt_password" # MQTT password (from broker setup)
  client_id: "fronius_bridge" # Unique client identifier
  topic_prefix: "homeassistant" # HA discovery topic prefix

application:
  poll_interval: 5            # Polling interval in seconds
  log_level: "INFO"          # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

diagnostic_sensors:           # Optional diagnostic sensor configuration
  enabled: true               # Global enable/disable for diagnostic sensors
  temperature:
    enabled: true             # Enable temperature sensors
    enabled_by_default: false # Temperature sensors disabled by default in HA
  operating_state:
    enabled: true             # Enable operating state sensors
    enabled_by_default: true  # Operating state sensors enabled by default in HA
  module_events:
    enabled: true             # Enable module events sensors
    enabled_by_default: false # Module events sensors disabled by default in HA
```

### Finding Your Inverter IP Address

1. **Router Admin Panel**: Check your router's DHCP client list
2. **Fronius Web Interface**: Access the inverter's web interface directly
3. **Network Scanner**: Use tools like `nmap` to scan your network:
   ```bash
   nmap -sn 192.168.1.0/24
   ```

### MQTT Broker Setup

This bridge requires an MQTT broker to communicate with Home Assistant. The most common setup is using Mosquitto:

#### Option 1: Home Assistant Add-on (Recommended)
1. Go to **Settings** → **Add-ons** → **Add-on Store**
2. Search for and install **Mosquitto broker**
3. Start the add-on and enable "Start on boot"
4. Go to **Settings** → **Devices & Services** → **Add Integration**
5. Search for and add **MQTT** integration
6. Configure with:
   - Broker: `localhost` (or your HA IP)
   - Port: `1883`
   - Username/Password: Create in Mosquitto add-on configuration

#### Option 2: External Mosquitto Broker
1. Install Mosquitto on a separate server
2. Create MQTT user credentials:
   ```bash
   sudo mosquitto_passwd -c /etc/mosquitto/passwd fronius_bridge
   ```
3. Configure Home Assistant MQTT integration to point to your broker
4. Use the same broker address and credentials in your config.yaml

#### MQTT Integration Setup
1. In Home Assistant: **Settings** → **Devices & Services** → **Add Integration**
2. Search for and select **MQTT**
3. Configure with your broker details:
   - Broker: Your MQTT broker IP/hostname
   - Port: `1883` (default)
   - Username: `fronius_bridge` (or your chosen username)
   - Password: The password you created
4. Enable **Discovery** to automatically detect bridge sensors

## Home Assistant Integration

### Automatic Discovery

The bridge automatically creates the following sensors in Home Assistant:

**Core MPPT Sensors** (always enabled):
- **PV1 Voltage** (V)
- **PV1 Current** (A)  
- **PV1 Power** (W)
- **PV2 Voltage** (V)
- **PV2 Current** (A)
- **PV2 Power** (W)
- **Total DC Power** (W)

**Diagnostic Sensors** (configurable):
- **MPPT1 Temperature** (°C) - *disabled by default*
- **MPPT1 Operating State** - *enabled by default*
- **MPPT1 Module Events** - *disabled by default*
- **MPPT2 Temperature** (°C) - *disabled by default*
- **MPPT2 Operating State** - *enabled by default*
- **MPPT2 Module Events** - *disabled by default*

All sensors are automatically grouped under a single device in Home Assistant using your inverter's serial number as the device identifier.

### Manual Configuration (if needed)

If auto-discovery doesn't work, add these sensors to your `configuration.yaml`:

```yaml
mqtt:
  sensor:
    # Core MPPT Sensors
    - name: "PV1 Voltage"
      state_topic: "homeassistant/sensor/fronius_<serial>/pv1_voltage/state"
      unit_of_measurement: "V"
      device_class: "voltage"
      value_template: "{{ value_json.voltage }}"
    
    - name: "Fronius MPPT1 Current"
      state_topic: "homeassistant/sensor/fronius_<serial>/mppt1_current/state"
      unit_of_measurement: "A"
      device_class: "current"
      value_template: "{{ value_json.current }}"
    
    # Diagnostic Sensors (optional)
    - name: "MPPT1 Temperature"
      state_topic: "homeassistant/sensor/fronius_<serial>/mppt1_temperature/state"
      unit_of_measurement: "°C"
      device_class: "temperature"
      entity_category: "diagnostic"
      value_template: "{{ value_json.temperature }}"
    
    - name: "MPPT1 Operating State"
      state_topic: "homeassistant/sensor/fronius_<serial>/mppt1_operating_state/state"
      device_class: "enum"
      entity_category: "diagnostic"
      value_template: "{{ value_json.state }}"
    
    - name: "MPPT1 Module Events"
      state_topic: "homeassistant/sensor/fronius_<serial>/mppt1_module_events/state"
      entity_category: "diagnostic"
      value_template: "{{ value_json.events }}"
    
    # ... (repeat for MPPT2 and other sensors)
```

Replace `<serial>` with your inverter's serial number.

## Diagnostic Sensors

The bridge provides comprehensive diagnostic monitoring capabilities through additional sensors that expose detailed health and operational information for each MPPT module.

### Available Diagnostic Sensors

#### Temperature Sensors
- **Purpose**: Monitor MPPT module temperatures to detect overheating conditions
- **Unit**: Celsius (°C)
- **Default State**: Disabled by default (can be enabled in Home Assistant)
- **Device Class**: Temperature
- **Example**: `MPPT1 Temperature`, `MPPT2 Temperature`

#### Operating State Sensors  
- **Purpose**: Display current operational mode of each MPPT module
- **Values**: OFF, SLEEPING, STARTING, MPPT, THROTTLED, SHUTTING_DOWN, FAULT, STANDBY, TEST, RESERVED_10
- **Default State**: Enabled by default
- **Device Class**: Enum
- **Example**: `MPPT1 Operating State`, `MPPT2 Operating State`

#### Module Events Sensors
- **Purpose**: Show active fault and event conditions for each MPPT module
- **Values**: Comma-separated list of active events or "No active events"
- **Default State**: Disabled by default (can be enabled in Home Assistant)
- **Events Include**: GROUND_FAULT, INPUT_OVER_VOLTAGE, DC_DISCONNECT, CABINET_OPEN, MANUAL_SHUTDOWN, OVER_TEMP, BLOWN_FUSE, UNDER_TEMP, MEMORY_LOSS, ARC_DETECTION, TEST_FAILED, INPUT_UNDER_VOLTAGE, INPUT_OVER_CURRENT
- **Example**: `MPPT1 Module Events`, `MPPT2 Module Events`

### Diagnostic Sensor Configuration

Diagnostic sensors can be configured globally or per sensor type:

```yaml
diagnostic_sensors:
  enabled: true                 # Master switch for all diagnostic sensors
  temperature:
    enabled: true               # Enable/disable temperature sensors
    enabled_by_default: false   # Default visibility in Home Assistant
  operating_state:
    enabled: true               # Enable/disable operating state sensors  
    enabled_by_default: true    # Default visibility in Home Assistant
  module_events:
    enabled: true               # Enable/disable module events sensors
    enabled_by_default: false   # Default visibility in Home Assistant
```

**Configuration Options**:
- `enabled: false` - Completely disables sensor type (not created in Home Assistant)
- `enabled_by_default: false` - Creates sensors but disables them by default in Home Assistant
- `enabled_by_default: true` - Creates sensors and enables them by default in Home Assistant

### Enabling Diagnostic Sensors in Home Assistant

Diagnostic sensors marked as disabled by default can be enabled through the Home Assistant interface:

1. **Navigate to Settings** → **Devices & Services**
2. **Find your Fronius device** (search for your inverter serial number)
3. **Click on the device** to view all entities
4. **Enable desired diagnostic sensors**:
   - Look for entities with names like "MPPT1 Temperature" or "MPPT2 Module Events"
   - Click the toggle switch to enable disabled sensors
   - Enabled sensors will start showing data immediately

### Diagnostic Sensor Examples

#### Normal Operation
```
MPPT1 Operating State: MPPT
MPPT1 Temperature: 45.2°C
MPPT1 Module Events: No active events

MPPT2 Operating State: MPPT  
MPPT2 Temperature: 43.8°C
MPPT2 Module Events: No active events
```

#### Fault Conditions
```
MPPT1 Operating State: FAULT
MPPT1 Temperature: 78.5°C
MPPT1 Module Events: OVER_TEMP, INPUT_OVER_VOLTAGE

MPPT2 Operating State: THROTTLED
MPPT2 Temperature: 52.1°C
MPPT2 Module Events: No active events
```

#### Startup/Shutdown
```
MPPT1 Operating State: STARTING
MPPT1 Temperature: 25.3°C
MPPT1 Module Events: No active events

MPPT2 Operating State: SLEEPING
MPPT2 Temperature: 24.8°C
MPPT2 Module Events: No active events
```

### Diagnostic Sensor Benefits

- **Proactive Monitoring**: Detect issues before they affect power production
- **Performance Optimization**: Identify thermal throttling and optimization opportunities
- **Maintenance Planning**: Schedule maintenance based on actual operating conditions
- **Fault Diagnosis**: Quickly identify and troubleshoot system problems
- **Historical Analysis**: Track long-term trends in module health and performance

### Troubleshooting Diagnostic Sensors

**Diagnostic sensors showing "unavailable"**:
- Check that your Fronius inverter supports SunSpec Model 160 diagnostic fields
- Verify Modbus connectivity is working (core MPPT sensors should be functional)
- Enable debug logging to see detailed diagnostic field reading attempts

**Diagnostic sensors not appearing**:
- Ensure `diagnostic_sensors.enabled: true` in your configuration
- Check individual sensor type enabled settings
- Restart the bridge application after configuration changes
- Look for diagnostic sensor creation errors in the application logs

**Temperature sensors showing unrealistic values**:
- Values outside -40°C to 150°C range are automatically marked as unavailable
- Check inverter firmware version - older versions may not support temperature readings
- Verify proper scaling is applied (should be in Celsius, not raw register values)

## Development Setup

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

2. **Run tests**:
   ```bash
   make test
   ```

3. **Run linting**:
   ```bash
   make lint
   ```

4. **Format code**:
   ```bash
   make format
   ```

5. **Run locally**:
   ```bash
   python -m src.fronius_modbus --config config.yaml
   ```

### Project Structure

```
fronius-ha-dual-mppt/
├── src/fronius_modbus/          # Main application code
│   ├── __init__.py
│   ├── __main__.py              # Entry point and main loop
│   ├── config.py                # Configuration management
│   ├── modbus_client.py         # Modbus/SunSpec client
│   └── mqtt_publisher.py        # MQTT publishing logic
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests
│   ├── property/                # Property-based tests
│   └── integration/             # Integration tests
├── Dockerfile                   # Docker container definition
├── docker-compose.yml          # Docker Compose configuration
├── Makefile                     # Build automation
├── config.yaml                  # Runtime configuration
├── config.example.yaml         # Configuration template
├── requirements.txt             # Python dependencies
└── requirements-dev.txt         # Development dependencies
```

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make help` | Show available targets |
| `make build` | Build Docker image |
| `make up` / `make start` | Start the application |
| `make down` / `make stop` | Stop the application |
| `make logs` | View application logs |
| `make test` | Run all tests |
| `make lint` | Run linting checks |
| `make format` | Format code |
| `make clean` | Clean up Docker resources |

## Troubleshooting

### Common Issues

1. **"Model 160 not found"**
   - Verify your Fronius inverter supports SunSpec Model 160
   - Check Modbus is enabled on the inverter
   - Confirm the correct IP address and unit ID

2. **"MQTT connection failed"**
   - Verify MQTT broker is running and accessible
   - Check username/password credentials
   - Ensure firewall allows MQTT traffic (port 1883/8883)

3. **"Modbus connection failed"**
   - Verify inverter IP address is correct
   - Check network connectivity: `ping <inverter-ip>`
   - Ensure Modbus TCP is enabled on the inverter

4. **Sensors not appearing in Home Assistant**
   - Check MQTT broker logs for discovery messages
   - Verify topic_prefix matches Home Assistant configuration
   - Restart Home Assistant after first discovery

5. **Diagnostic sensors showing "unavailable"**
   - Verify your inverter supports SunSpec Model 160 diagnostic fields (Tmp, DCSt, DCEvt)
   - Check that core MPPT sensors are working (diagnostic sensors depend on same Model 160 data)
   - Enable debug logging to see diagnostic field reading attempts
   - Some older inverter firmware versions may not support all diagnostic fields

6. **Diagnostic sensors not created**
   - Ensure `diagnostic_sensors.enabled: true` in configuration
   - Check individual sensor type settings (temperature, operating_state, module_events)
   - Restart the bridge application after configuration changes
   - Review application logs for diagnostic sensor creation errors

### Debug Mode

Enable debug logging for detailed troubleshooting:

```yaml
application:
  log_level: "DEBUG"
```

### Network Connectivity Test

Test Modbus connectivity:
```bash
# Test basic connectivity
ping <inverter-ip>

# Test Modbus port
telnet <inverter-ip> 502
```

## SunSpec Model 160 Requirements

This bridge specifically requires **SunSpec Model 160** (Multiple MPPT Inverter Extension) support. This model provides:

**Core MPPT Data**:
- Individual MPPT channel voltage readings
- Individual MPPT channel current readings  
- Individual MPPT channel power readings
- Total DC power output

**Diagnostic Data** (when available):
- MPPT module temperature readings (Tmp field)
- Operating state information (DCSt field) 
- Module event and fault conditions (DCEvt field)

The diagnostic features require inverters with full Model 160 implementation including the optional diagnostic fields. Core MPPT monitoring will work even if diagnostic fields are not available.

### Supported Fronius Models

Most Fronius Symo inverters support Model 160, including:
- Fronius Symo 3.0-3-M
- Fronius Symo 4.5-3-M
- Fronius Symo 5.0-3-M
- Fronius Symo 6.0-3-M
- Fronius Symo 7.0-3-M
- Fronius Symo 8.2-3-M
- Fronius Symo 10.0-3-M
- Fronius Symo 15.0-3-M
- Fronius Symo 17.5-3-M
- Fronius Symo 20.0-3-M

### Verifying Model 160 Support

You can verify Model 160 support using SunSpec tools or by checking the bridge logs during startup.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Run linting: `make lint`
6. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the application logs: `make logs`
3. Open an issue on GitHub with:
   - Your configuration (with sensitive data removed)
   - Application logs
   - Fronius inverter model
   - Home Assistant version