# Fronius HA Dual MPPT

Reads extended MPPT data from Fronius inverters via SunSpec Model 160 Modbus and publishes to Home Assistant via MQTT discovery. Provides per-string DC monitoring that the native Fronius HA integration doesn't expose.

![Dual MPPT Data in Home Assistant](./media/Dual%20MMPT%20Data%20in%20HA.png)

## Features

- Per-string voltage, current, and power (PV1 + PV2)
- Total DC power
- Diagnostic sensors: operating state, temperature, module events (model-dependent)
- Controller uptime and configuration exposed as HA entities
- Auto-reconnection with exponential backoff for both Modbus and MQTT
- Multi-arch Docker image (amd64 + arm64)

## Getting Started

1. Copy and edit the config file:
   ```bash
   cp config.example.yaml config.yaml
   # Edit with your inverter IP, MQTT broker details
   ```

2. Run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

## Inverter Setup

Modbus TCP must be enabled on the inverter:

1. Open the inverter web UI (`http://<inverter-ip>`)
2. Log in as **service** (not the customer password — check the sticker inside the inverter or your installer documentation)
3. **Settings → Communication → Modbus** — enable Modbus TCP, port `502`, unit ID `1`

## Configuration

Minimal `config.yaml`:

```yaml
modbus:
  host: "192.168.1.100"
  port: 502
  unit_id: 1
  timeout: 10

mqtt:
  broker: "192.168.1.50"
  port: 1883
  username: "ha_user"
  password: "secret"
  client_id: "fronius_bridge"
  topic_prefix: "homeassistant"

application:
  poll_interval: 5
  mqtt_republish_rate: 300
  logging:
    level: "INFO"
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

Diagnostic sensors are enabled by default. See `config.example.yaml` for the full `diagnostic_sensors` block if you want to disable individual sensor types.

## Sensors

All sensors are auto-discovered under a single HA device using the inverter serial number.

| Sensor | Type | Notes |
|--------|------|-------|
| PV1/PV2 Voltage, Current, Power | measurement | Always available |
| Total DC Power | measurement | Always available |
| Operating State | diagnostic | ✅ Most Fronius Symo models |
| Temperature | diagnostic | ⚠️ Limited Symo support |
| Module Events | diagnostic | ⚠️ Limited Symo support |
| Controller Uptime | diagnostic | Seconds since start |
| Modbus/Application config | config | Exposed as HA number/text entities |

Unsupported diagnostic fields show as "unavailable" without affecting core sensors.

## Development

```bash
make test      # Run all tests
make lint      # Lint with ruff
make format    # Auto-format with ruff
make build     # Build Docker image
make push      # Build & push multi-arch (amd64 + arm64)
```

## CI/CD

GitHub Actions runs lint + tests on every push. Docker images are built for amd64 and arm64 on every push, but only pushed to DockerHub on `main` and version tags. Creating a release:

```bash
git tag -a v0.1.0 -m "Initial release"
git push origin v0.1.0
```

Requires `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets in repo settings.

## License

MIT
