# bacnet-sim-ci

[![CI](https://github.com/Rise-Building-Technology/bacnet-sim-ci/actions/workflows/ci.yml/badge.svg)](https://github.com/Rise-Building-Technology/bacnet-sim-ci/actions/workflows/ci.yml)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

BACnet device simulator for CI pipelines. Runs as a Docker container or GitHub Action to provide virtual BACnet/IP devices for integration testing.

## Quick Start

### GitHub Actions (Service Container — REST-only)

For tests that only use the HTTP REST API:

```yaml
services:
  bacnet-sim:
    image: ghcr.io/rise-building-technology/bacnet-sim-ci:latest
    ports:
      - 47808:47808/udp
      - 8099:8099
    options: >-
      --cap-add=NET_ADMIN
      --health-cmd "curl -f http://localhost:8099/health/ready || exit 1"
      --health-interval 5s
      --health-timeout 3s
      --health-retries 10
      --health-start-period 15s
```

**If your test client speaks BACnet/IP UDP directly, do not use the `services:` pattern** — docker-proxy drops UDP packets across the bridge. See [Networking → Choosing a pattern](#choosing-a-pattern) and [`examples/workflow-bacnet-protocol.yml`](examples/workflow-bacnet-protocol.yml).

### GitHub Action

```yaml
- uses: rise-building-technology/bacnet-sim-ci@v1
  with:
    device-id: "1001"
    device-name: "TestDevice"
```

### Docker

```bash
docker run -d \
  --cap-add=NET_ADMIN \
  -p 47808:47808/udp \
  -p 8099:8099 \
  ghcr.io/rise-building-technology/bacnet-sim-ci:latest
```

## Features

- **Multi-device simulation** in a single container using virtual IPs (all on port 47808)
- **Extended BACnet objects**: Analog I/O, Binary I/O, Multistate Value, Character String
- **Value mutation** via BACnet WriteProperty and HTTP REST API
- **Network lag simulation** with configurable profiles
- **Zero-config default**: generic HVAC controller works out of the box
- **Who-Is/I-Am discovery** works across all simulated devices

## Configuration

### YAML Config File

Mount a YAML file to define devices and objects:

```yaml
global:
  api_port: 8099
  bacnet_port: 47808
  network_profile: local-network

devices:
  - device_id: 1001
    name: "AHU-1"
    objects:
      - type: analog-input
        instance: 1
        name: "Zone Temp"
        unit: degreesFahrenheit
        value: 72.5
      - type: analog-output
        instance: 1
        name: "Setpoint"
        unit: degreesFahrenheit
        value: 72.0
        commandable: true
      - type: binary-output
        instance: 1
        name: "Fan Command"
        inactive_text: "Off"
        active_text: "On"
        value: false
        commandable: true
```

```bash
docker run --cap-add=NET_ADMIN \
  -v ./config.yaml:/app/config/config.yaml \
  -e CONFIG_FILE=/app/config/config.yaml \
  ghcr.io/rise-building-technology/bacnet-sim-ci:latest
```

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `BACNET_DEVICE_ID` | First device's ID | `1001` |
| `BACNET_DEVICE_NAME` | First device's name | `SimDevice` |
| `BACNET_PORT` | BACnet UDP port | `47808` |
| `API_PORT` | REST API port | `8099` |
| `NETWORK_PROFILE` | Network lag profile | `none` |
| `CONFIG_FILE` | Path to YAML config | (built-in default) |

**Precedence:** Environment variables > YAML config > built-in defaults.

### Supported Object Types

| Type | YAML key | Commandable |
|---|---|---|
| Analog Input | `analog-input` | No (by default) |
| Analog Output | `analog-output` | Yes |
| Binary Input | `binary-input` | No (by default) |
| Binary Output | `binary-output` | Yes |
| Multistate Value | `multistate-value` | Optional |
| Character String | `character-string` | Optional |

Set `commandable: true` on any object to allow BACnet WriteProperty.

### Device Templates

Built-in templates provide pre-defined object lists for common HVAC equipment, reducing config boilerplate:

```yaml
devices:
  - device_id: 1001
    name: "AHU-1"
    template: ahu

  - device_id: 1002
    name: "VAV-201"
    template: vav

  - device_id: 1003
    name: "Boiler-1"
    template: boiler
    objects:  # extend/override template objects
      - type: analog-input
        instance: 100
        name: "Custom Sensor"
        unit: degreesFahrenheit
        value: 180.0
```

| Template | Objects | Description |
|---|---|---|
| `ahu` | 17 | Air handling unit — temps, pressures, dampers, fans, filters |
| `vav` | 10 | Variable air volume box — zone temp, airflow, damper, reheat |
| `boiler` | 14 | Boiler — supply/return temps, firing rate, pumps, safeties |
| `meter` | 11 | Energy/utility meter — power, energy, voltage, current, demand |

When `template:` and `objects:` are both specified, explicit objects are appended to the template objects.

### Default Device (Zero Config)

When no config is provided, the simulator starts a single HVAC controller:

| Object | Type | Instance | Default Value |
|---|---|---|---|
| Zone Temp | analog-input | 1 | 72.5 |
| Supply Air Temp | analog-input | 2 | 55.0 |
| Zone Setpoint | analog-output | 1 | 72.0 |
| Fan Status | binary-input | 1 | Active |
| Fan Command | binary-output | 1 | Inactive |
| Damper Position | analog-output | 2 | 50.0 |
| Occupancy Mode | multistate-value | 1 | 1 (Auto) |
| Device Status | character-string | 1 | "Normal" |

## REST API

The simulator exposes a REST API on port 8099 (configurable). OpenAPI docs at `/docs`.

### Health Check

```bash
# Liveness (process running)
curl http://localhost:8099/health/live

# Readiness (all devices initialized)
curl http://localhost:8099/health/ready
```

### Device Discovery

```bash
# List all devices with IPs
curl http://localhost:8099/api/devices
```

```json
[
  {
    "deviceId": 1001,
    "name": "AHU-1",
    "ip": "172.18.0.10",
    "port": 47808,
    "objectCount": 3,
    "initialized": true
  }
]
```

### Read/Write Objects

```bash
# Read
curl http://localhost:8099/api/devices/1001/objects/analog-input/1

# Write
curl -X PUT http://localhost:8099/api/devices/1001/objects/analog-input/1 \
  -H "Content-Type: application/json" \
  -d '{"value": 75.0}'
```

### Change Network Profile at Runtime

```bash
curl -X PUT http://localhost:8099/api/devices/1001/network-profile \
  -H "Content-Type: application/json" \
  -d '{"profile": "unreliable-link"}'
```

## Network Lag Simulation

Simulate real-world network conditions per device:

| Profile | Delay | Drop Rate | Use Case |
|---|---|---|---|
| `none` | 0ms | 0% | Default, no simulation |
| `local-network` | 0-10ms | 0% | Fast local BACnet |
| `remote-site` | 50-200ms | 1% | WAN/VPN connection |
| `unreliable-link` | 200-1000ms | 10% | Spotty cellular link |
| `custom` | User-defined | User-defined | Any scenario |

Lag applies only to BACnet responses. The HTTP API always responds immediately.

## Multi-Device Architecture

Multiple devices run in a single container using virtual IPs:

- Each device gets a unique IP address on the container's network interface
- All devices bind to port 47808 (standard BACnet/IP)
- **Who-Is/I-Am broadcast discovery works** across all devices
- Requires `--cap-add=NET_ADMIN` (for `ip addr add`)

IPs are auto-assigned sequentially from the container's primary IP, or can be explicitly set per device in the YAML config.

## Networking

### Docker Bridge

The simulator and your test client must be on the **same Docker network**. BACnet/IP uses UDP broadcast for device discovery, which only works within a single Docker network.

### Docker Compose

```yaml
services:
  bacnet-sim:
    image: ghcr.io/rise-building-technology/bacnet-sim-ci:latest
    cap_add:
      - NET_ADMIN
    networks:
      - bacnet

  your-app:
    build: .
    networks:
      - bacnet

networks:
  bacnet:
    driver: bridge
```

### GitHub Actions

#### Choosing a pattern

| Your test client uses... | Use this pattern | Example |
|---|---|---|
| HTTP REST API only | `services:` container | [`workflow-service-container.yml`](examples/workflow-service-container.yml) |
| BACnet/IP UDP directly | Sibling-container on a custom network | [`workflow-bacnet-protocol.yml`](examples/workflow-bacnet-protocol.yml) |

The `services:` keyword routes container ports through docker-proxy. TCP (REST) works fine, but **UDP packets are unreliable across the bridge** — BACnet `readProperty` / Who-Is calls time out even when the REST healthcheck passes. If your tests use BACnet protocol calls, run your test client as a sibling container on a custom Docker network with fixed IPs so UDP becomes a direct peer-to-peer flow with no NAT.

If REST works but your BACnet client gets timeouts, the test client is almost certainly on the runner host instead of inside a sibling container.

#### Healthcheck context

The `--health-cmd` from the `services:` example runs **inside the simulator's own container**, where `localhost:8099` is the sim's REST API. From the runner host you reach the API via the `ports:` mapping (`localhost:8099`); from a sibling container you reach it directly by service hostname (`bacnet-sim:8099`).

#### Pinning the image for deterministic CI

`:latest` follows new builds and can change without warning. For reproducible CI, pin by digest:

```yaml
image: ghcr.io/rise-building-technology/bacnet-sim-ci@sha256:29ed481aa6015dc3508a5aec5b2cb5a69c86bdc2ef22bb7ecb0d75c0d7745963
```

Get the current digest with:

```bash
docker buildx imagetools inspect ghcr.io/rise-building-technology/bacnet-sim-ci:latest
```

Bump the digest in your workflow after testing the new build locally.

#### Image platforms

Published as a multi-arch manifest covering `linux/amd64` and `linux/arm64`. Verify with `docker manifest inspect ghcr.io/rise-building-technology/bacnet-sim-ci:latest`.

## Resource Usage

| Devices | Approximate Memory | Recommended Runner |
|---|---|---|
| 1 (default) | ~80 MB | Any (ubuntu-latest) |
| 5 | ~200 MB | ubuntu-latest |
| 10 | ~350 MB | ubuntu-latest |
| 20+ | ~600 MB+ | Large runner recommended |

Each BAC0 device instance uses roughly 30-50 MB. The base process (Python + FastAPI) uses ~50 MB.

## Limitations

- **Requires `--cap-add=NET_ADMIN`** for multi-device virtual IP setup
- **BACnet/IP only** (no MSTP, no BACnet/SC)
- **No COV subscriptions** (Change of Value notifications)
- **No BBMD** (Broadcast Management Device)
- **Test client must be on the same Docker network** for BACnet broadcast discovery (and a sibling container, not the runner host — see [Networking → Choosing a pattern](#choosing-a-pattern))

## Development

```bash
# Install
pip install -e ".[dev]"

# Test
pytest tests/ -v

# Lint
ruff check src/ tests/

# Build Docker image
docker build -t bacnet-sim-ci .
```

## License

LGPL-3.0-or-later (inherited from [BAC0](https://github.com/ChristianTremblay/BAC0))
