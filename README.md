# Fronius HA Dual MPPT

Sends solar inverter DC data to Home Assistant via MQTT, for both solar arrays. This application reads extended MPPT (Maximum Power Point Tracking) data from the inverter using the Modbus protocol and publishes it to an MQTT broker with Home Assistant auto-discovery support. Although the native Fronius integration in Home Assistant works well, it doesn't seem to report this extended data offered by inverters that support the Sunspec API, with model 160 extension as is the case for Fronius Symo.

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
- **Home Assistant Integration**: Automatic sensor discovery via MQTT
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

The application uses a YAML configuration file with three main sections:

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

- **PV1 Voltage** (V)
- **PV1 Current** (A)  
- **PV1 Power** (W)
- **PV2 Voltage** (V)
- **PV2 Current** (A)
- **PV2 Power** (W)
- **Total DC Power** (W)

### Manual Configuration (if needed)

If auto-discovery doesn't work, add these sensors to your `configuration.yaml`:

```yaml
mqtt:
  sensor:
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
    
    # ... (repeat for other sensors)
```

Replace `<serial>` with your inverter's serial number.

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

- Individual MPPT channel voltage readings
- Individual MPPT channel current readings  
- Individual MPPT channel power readings
- Total DC power output

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