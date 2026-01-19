# Fronius HA Dual MPPT

Reads extended MPPT data from Fronius Symo inverters via Modbus and publishes to Home Assistant via MQTT. Provides individual string monitoring that the native Fronius Home Assistant integration doesn't offer.

![Dual MPPT Data in Home Assistant](./media/Dual%20MMPT%20Data%20in%20HA.png)

## Quick Start

```bash
# Pull and run with Docker
docker pull lerebel103/fronius-ha-dual-mppt:latest
docker run -d --name fronius-ha-dual-mppt --network host \
  -v ./config.yaml:/etc/fronius-mppt-bridge/config.yaml:ro \
  --restart unless-stopped lerebel103/fronius-ha-dual-mppt:latest

# Or use docker-compose
git clone <repository-url>
cd fronius-ha-dual-mppt
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
make up
```

## Features

- **Individual MPPT monitoring**: Voltage, current, power for each string
- **Diagnostic sensors**: Operating state, temperature, module events (model-dependent)
- **Home Assistant integration**: Auto-discovery with proper entity categories
- **Resilient operation**: Auto-reconnection, graceful error handling
- **Docker support**: Easy containerized deployment

## Setup

### 1. Enable Modbus on Fronius Inverter

1. Access inverter web interface: `http://192.168.1.XXX`
2. Login with **service** user (not customer password - check inverter sticker/documentation)
3. Navigate to **Settings** → **Communication** → **Modbus**
4. Enable **Modbus TCP**, set port `502`, unit ID `1`

### 2. Configure MQTT Broker

Set up MQTT broker in Home Assistant (**Settings** → **Add-ons** → **Mosquitto broker**) or use external broker.

### 3. Configure Bridge

Edit `config.yaml`:

```yaml
modbus:
  host: "192.168.1.100"    # Your inverter IP
  port: 502
  unit_id: 1
  timeout: 10

mqtt:
  broker: "192.168.1.50"   # Your MQTT broker IP
  port: 1883
  username: "fronius_bridge"
  password: "your_password"
  client_id: "fronius_bridge"
  topic_prefix: "homeassistant"

application:
  poll_interval: 5
  mqtt_republish_rate: 300
  logging:
    level: "INFO"
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Optional diagnostic sensors
diagnostic_sensors:
  enabled: true
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

## Sensors Created

**Core MPPT Sensors** (always available):
- PV1/PV2 Voltage, Current, Power
- Total DC Power

**Diagnostic Sensors** (model-dependent):
- **Operating State**: ✅ Supported on most Fronius Symo models
- **Temperature**: ⚠️ Limited support on Fronius Symo models  
- **Module Events**: ⚠️ Limited support on Fronius Symo models

Unsupported diagnostic sensors will show as "unavailable" - this is normal and doesn't affect core functionality.

## Troubleshooting

**"Model 160 not found"**: Verify Modbus is enabled and inverter supports SunSpec Model 160

**"MQTT connection failed"**: Check broker IP, credentials, and firewall settings

**"Modbus connection failed"**: Verify inverter IP and network connectivity

**Diagnostic sensors "unavailable"**: Normal for many Fronius Symo models - only Operating State is widely supported

**Sensors not appearing**: Check MQTT discovery is enabled in Home Assistant, verify topic_prefix matches

## Development

```bash
# Local development
pip install -r requirements.txt requirements-dev.txt
python -m src.fronius_modbus --config config.yaml

# Testing
make test
make lint
make format
```

## Supported Models

Most Fronius Symo inverters (3.0-3-M through 20.0-3-M) support core MPPT monitoring. Diagnostic sensor availability varies by model and firmware version.

## License

MIT License - see LICENSE file for details.