---
title: "feat: BACnet Device Simulator for GitHub CI"
type: feat
status: completed
date: 2026-02-15
brainstorm: docs/brainstorms/2026-02-15-bacnet-sim-ci-brainstorm.md
---

# BACnet Device Simulator for GitHub CI

## Overview

A public, open-source BACnet/IP device simulator packaged as a Docker container and GitHub Action. Consumers pull it into CI pipelines (or run locally) to integration-test their BACnet client software against realistic virtual devices. Published to `ghcr.io/rise-building-technology/bacnet-sim-ci`.

**Key capabilities:**
- Multi-device simulation in a single container (virtual IPs, all on port 47808)
- Extended BACnet object set (AI/AO, BI/BO, MSV, CharString, Schedule, TrendLog)
- Value mutation via BACnet WriteProperty and HTTP REST API
- Configurable network lag profiles (local, remote, unreliable, custom)
- Zero-config default: generic HVAC controller works out of the box

## Problem Statement / Motivation

Teams building BACnet client software need a way to run integration tests in CI without physical BACnet devices. Existing open-source simulators are either not containerized, not designed for CI consumption, or lack configurability. This project fills that gap with a purpose-built, CI-first simulator that can be added to a GitHub Actions workflow in 5 lines of YAML.

## Technical Approach

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Docker Container (--cap-add=NET_ADMIN)                  │
│                                                          │
│  eth0: 172.18.0.10/24  (primary)                         │
│  eth0: 172.18.0.11/24  (virtual)                         │
│  eth0: 172.18.0.12/24  (virtual)                         │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ BAC0 Device   │  │ BAC0 Device   │  │ BAC0 Device  │  │
│  │ ID: 1001      │  │ ID: 1002      │  │ ID: 1003     │  │
│  │ IP: .10:47808 │  │ IP: .11:47808 │  │ IP: .12:47808│  │
│  │ + Lag Layer   │  │ + Lag Layer   │  │ + Lag Layer  │  │
│  └───────┬───────┘  └───────┬───────┘  └──────┬───────┘  │
│          │ UDP               │ UDP             │ UDP      │
│          └───────────────────┴─────────────────┘         │
│          All on port 47808, same subnet                  │
│          Who-Is/I-Am broadcast discovery works            │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │ FastAPI (0.0.0.0:8099)                           │    │
│  │  GET  /health/live    — process alive            │    │
│  │  GET  /health/ready   — all devices initialized  │    │
│  │  GET  /api/devices    — list devices + IPs       │    │
│  │  GET  /api/devices/{id}/objects                  │    │
│  │  GET  /api/devices/{id}/objects/{type}/{inst}    │    │
│  │  PUT  /api/devices/{id}/objects/{type}/{inst}    │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

**Key architectural decisions:**

1. **All devices on the same BACnet network (port 47808) using virtual IPs.** BAC0 cannot bind two instances to the same IP:port. We assign each device a unique virtual IP on the container's network interface via `ip addr add`. All bind to port 47808 on the same subnet. This means **Who-Is/I-Am broadcast discovery works** — all devices see each other and can be discovered by clients on the same Docker network.

2. **Container requires `NET_ADMIN` capability** to add virtual IPs at runtime. The entrypoint script runs `ip addr add <ip>/24 dev eth0` for each additional device before starting the Python process.

3. **FastAPI and BAC0 share a single asyncio event loop.** Uvicorn runs programmatically via `uvicorn.Server.serve()` as a coroutine alongside BAC0's async context managers, all inside `asyncio.run(main())`.

4. **Network lag is applied at the BACnet application layer** using `asyncio.sleep()` before constructing responses. Lag does NOT affect the HTTP API (always fast). Each device has its own lag profile.

5. **Health check is two-tier:** `/health/live` (process running) and `/health/ready` (all BAC0 devices initialized + all objects registered). Docker HEALTHCHECK targets `/health/ready`.

6. **The test client must be on the same Docker network** as the simulator container. In GitHub Actions, this means using a service container on the default bridge, or using Docker Compose with a shared network. The client communicates with each device by its virtual IP on port 47808.

### Multi-Device IP Allocation

On startup, the entrypoint script:
1. Reads the container's primary IP from the network interface (e.g., `172.18.0.10`)
2. Assigns the first device to the primary IP
3. For each additional device, adds a virtual IP by incrementing the host portion (e.g., `172.18.0.11`, `172.18.0.12`, ...)
4. YAML config can explicitly assign IPs per device

| Devices in config | IP assignment |
|---|---|
| 1 device (default) | Container's primary IP |
| N devices (auto) | Primary IP, primary+1, primary+2, ... |
| N devices (explicit) | User-specified per-device in YAML |

**Conflict handling:** If a virtual IP is already in use on the network, the container logs the error, marks the device as failed, and `/health/ready` returns `503`. If ALL devices fail, the container exits with code 1.

### YAML Configuration Schema

```yaml
# config.yaml
global:
  api_port: 8099              # FastAPI port (default: 8099)
  bacnet_port: 47808          # BACnet UDP port, all devices (default: 47808)
  subnet_mask: 24             # Subnet mask for virtual IPs (default: 24)
  network_profile: local-network  # Default profile for all devices

devices:
  - device_id: 1001
    name: "AHU-1"
    ip: "172.18.0.11"         # Optional: explicit IP override (auto-assigned if omitted)
    network_profile: remote-site  # Optional: per-device override
    network_custom:            # Only used when profile is "custom"
      min_delay_ms: 100
      max_delay_ms: 500
      drop_probability: 0.05
    objects:
      - type: analog-input
        instance: 1
        name: "Zone Temp"
        unit: degreesCelsius
        value: 72.5
      - type: analog-output
        instance: 1
        name: "Setpoint"
        unit: degreesCelsius
        value: 72.0
        commandable: true
      - type: binary-input
        instance: 1
        name: "Fan Status"
        inactive_text: "Off"
        active_text: "On"
        value: true
      - type: binary-output
        instance: 1
        name: "Fan Command"
        inactive_text: "Off"
        active_text: "On"
        value: false
        commandable: true
      - type: multistate-value
        instance: 1
        name: "Occupancy Mode"
        states: ["Auto", "Occupied", "Unoccupied", "Standby"]
        value: 1
        commandable: true
      - type: character-string
        instance: 1
        name: "Status"
        value: "Normal"
        commandable: true
```

**Environment variable overrides** (for simple single-device cases):

| Env var | Overrides | Default |
|---|---|---|
| `BACNET_DEVICE_ID` | First device's ID | `1001` |
| `BACNET_DEVICE_NAME` | First device's name | `SimDevice` |
| `BACNET_PORT` | BACnet UDP port (all devices) | `47808` |
| `BACNET_SUBNET_MASK` | Subnet mask for virtual IPs | `24` |
| `API_PORT` | FastAPI port | `8099` |
| `NETWORK_PROFILE` | Global network profile | `local-network` |
| `CONFIG_FILE` | Path to YAML config | (built-in default) |

**Precedence:** Env vars > YAML config > built-in defaults.

### REST API Design

All endpoints return JSON. FastAPI auto-generates OpenAPI docs at `/docs`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health/live` | Returns `200` if process is running |
| `GET` | `/health/ready` | Returns `200` when all devices initialized, `503` otherwise |
| `GET` | `/api/devices` | List all devices with IDs, names, IPs, object counts |
| `GET` | `/api/devices/{deviceId}/objects` | List objects for a device |
| `GET` | `/api/devices/{deviceId}/objects/{objectType}/{instance}` | Read object properties (presentValue, statusFlags, etc.) |
| `PUT` | `/api/devices/{deviceId}/objects/{objectType}/{instance}` | Write presentValue (body: `{"value": ...}`) |
| `PUT` | `/api/devices/{deviceId}/network-profile` | Change network profile at runtime |

**HTTP writes vs BACnet writes:** HTTP `PUT` sets `presentValue` directly (bypasses priority array). BACnet `WriteProperty` goes through the priority array on commandable objects. Both modify the same in-memory BAC0 object, so reads from either path see the latest value.

### Network Lag Profiles

| Profile | Min delay | Max delay | Drop probability | Use case |
|---|---|---|---|---|
| `local-network` | 0ms | 10ms | 0% | Fast local BACnet network |
| `remote-site` | 50ms | 200ms | 1% | WAN/VPN to remote building |
| `unreliable-link` | 200ms | 1000ms | 10% | Spotty cellular/satellite link |
| `custom` | User-defined | User-defined | User-defined | Any scenario |
| `none` | 0ms | 0ms | 0% | No simulation (default behavior) |

**Implementation:** A middleware wrapper around BAC0's response handling. Before sending a BACnet response:
1. Check device's lag profile
2. If drop: silently discard the response (client sees timeout)
3. Else: `await asyncio.sleep(random.uniform(min_delay, max_delay) / 1000)`
4. Then send the response

Lag applies **only to BACnet responses**, never to the HTTP API.

### Default HVAC Controller (Zero-Config)

When no config file is provided, the simulator starts a single device:

| Object | Type | Instance | Name | Default Value | Commandable |
|---|---|---|---|---|---|
| Device | device | 1001 | "HVAC Controller" | — | — |
| Zone Temp | analog-input | 1 | "Zone Temp" | 72.5 F | No |
| Supply Temp | analog-input | 2 | "Supply Air Temp" | 55.0 F | No |
| Setpoint | analog-output | 1 | "Zone Setpoint" | 72.0 F | Yes |
| Fan Status | binary-input | 1 | "Fan Status" | Active | No |
| Fan Command | binary-output | 1 | "Fan Command" | Inactive | Yes |
| Damper Cmd | analog-output | 2 | "Damper Position" | 50.0 % | Yes |
| Occ Mode | multistate-value | 1 | "Occupancy Mode" | 1 (Auto) | Yes |
| Status Text | character-string | 1 | "Device Status" | "Normal" | Yes |

### BACnet Protocol Support (v1)

| Feature | Supported | Notes |
|---|---|---|
| ReadProperty | Yes | Via BAC0/BACpypes3 |
| ReadPropertyMultiple | Yes | Via BAC0/BACpypes3 |
| WriteProperty | Yes | On commandable objects |
| WritePropertyMultiple | Yes | Via BAC0/BACpypes3 |
| Who-Is / I-Am | Yes | All devices on same port/subnet — broadcast discovery works |
| Who-Has / I-Has | Yes | Via BAC0/BACpypes3 |
| Priority Array | Yes | On commandable objects (16 levels) |
| Segmentation | Depends | BAC0/BACpypes3 default behavior |
| COV Subscriptions | No | Out of scope for v1 |
| BACnet/SC | No | Out of scope |
| BBMD | No | Out of scope |

## Implementation Phases

### Phase 1: Project Scaffolding and Core Simulator

**Goal:** Working single-device simulator with default HVAC config, no HTTP API yet.

**Files to create:**

```
bacnet-sim-ci/
  src/
    bacnet_sim/
      __init__.py
      main.py              # Entry point: asyncio.run(main())
      config.py            # YAML + env var config loading, Pydantic models
      devices.py           # BAC0 device creation from config
      networking.py         # Virtual IP allocation (ip addr add)
      defaults.py          # Default HVAC controller config
  config/
    default.yaml           # Default device config (matches defaults.py)
    example-multi-device.yaml
  scripts/
    entrypoint.sh          # Docker entrypoint: setup virtual IPs, then exec python
  tests/
    __init__.py
    conftest.py
    test_config.py         # Config loading and validation tests
    test_devices.py        # Device creation tests
    test_networking.py     # Virtual IP allocation tests
  pyproject.toml           # Project metadata, dependencies
  requirements.txt         # Pinned deps for Docker
  .gitignore
  .python-version          # 3.11
```

**Tasks:**

- [x] Initialize git repo and Python project (`pyproject.toml` with BAC0, pydantic, pyyaml)
- [x] Create Pydantic models for config schema (`config.py`): `DeviceConfig`, `ObjectConfig`, `NetworkProfile`, `SimulatorConfig`
- [x] Implement config loading: YAML file parsing, env var overrides, defaults fallback (`config.py`)
- [x] Implement config validation: unique device IDs, unique object names per device, valid object types, unique IPs if explicitly set (`config.py`)
- [x] Implement virtual IP allocation (`networking.py`): detect container's primary IP and subnet, compute virtual IPs for additional devices, add IPs via `ip addr add` (subprocess), cleanup on shutdown
- [x] Create `entrypoint.sh`: read config to determine device count, add virtual IPs, then `exec python -m bacnet_sim.main`
- [x] Create BAC0 device factory (`devices.py`): takes `DeviceConfig` + assigned IP, creates `BAC0.lite(ip=assigned_ip, port=47808, ...)`, registers objects via factory functions, supports all extended object types
- [x] Create default HVAC controller config (`defaults.py`)
- [x] Wire up entry point (`main.py`): load config, create devices (each bound to its virtual IP on port 47808), keep running
- [x] Write unit tests for config loading, validation, IP allocation, and device creation

**Success criteria:** `python -m bacnet_sim.main` starts BAC0 devices on virtual IPs, all on port 47808. A BACnet client on the same subnet can discover all devices via Who-Is and ReadProperty/WriteProperty them.

### Phase 2: FastAPI REST API and Health Checks

**Goal:** HTTP API for value mutation and health checks, running alongside BAC0 in the same async loop.

**Files to create/modify:**

```
  src/
    bacnet_sim/
      api.py               # FastAPI app, routes, lifespan
      health.py            # Health check logic (live + ready)
```

**Tasks:**

- [x] Create FastAPI app with lifespan context manager (`api.py`)
- [x] Implement health check endpoints: `/health/live` (always 200), `/health/ready` (200 only when all devices initialized) (`health.py`)
- [x] Implement device listing: `GET /api/devices` returns `[{deviceId, name, ip, objectCount}]`
- [x] Implement object listing: `GET /api/devices/{id}/objects` returns object metadata
- [x] Implement object read: `GET /api/devices/{id}/objects/{type}/{instance}` returns presentValue + properties
- [x] Implement object write: `PUT /api/devices/{id}/objects/{type}/{instance}` body `{"value": ...}`
- [x] Integrate FastAPI with BAC0 in `main.py`: use `uvicorn.Server.serve()` in the same async loop
- [x] Wire up startup ordering: BAC0 devices first, then FastAPI
- [x] Write tests for all API endpoints

**Success criteria:** Container starts, `/health/ready` returns 200 after all devices initialize. API can read/write all object types. OpenAPI docs available at `/docs`.

### Phase 3: Network Lag Simulation

**Goal:** Configurable per-device latency and request drops.

**Files to create/modify:**

```
  src/
    bacnet_sim/
      lag.py               # Lag middleware / delay injection
```

**Tasks:**

- [x] Define lag profile dataclass with min/max delay, drop probability (`lag.py`)
- [x] Implement lag injection: hook into BAC0/BACpypes3 response path to add `asyncio.sleep()` before sending
- [x] Implement request drop: probabilistic discard (no response sent, client sees timeout)
- [x] Add `PUT /api/devices/{id}/network-profile` to change profile at runtime
- [x] Integrate lag config with YAML schema and env var overrides
- [x] Write tests: verify delay ranges, verify drop behavior, verify HTTP API is unaffected

**Success criteria:** A device with `unreliable-link` profile shows measurable latency and occasional timeouts. A device with `local-network` profile responds quickly. HTTP API always responds immediately.

### Phase 4: Docker Container and CI Pipeline

**Goal:** Published Docker image on ghcr.io with CI pipeline.

**Files to create:**

```
  Dockerfile
  .dockerignore
  docker-compose.yml       # Local dev + multi-device testing
  .github/
    workflows/
      ci.yml               # Build, test, publish
```

**Tasks:**

- [x] Write multi-stage `Dockerfile`: `python:3.11-slim-bookworm` base, install `iproute2` (for `ip addr add`), HEALTHCHECK, expose UDP 47808 and TCP 8099. Note: container needs `--cap-add=NET_ADMIN` at runtime for virtual IPs (cannot run as non-root for the IP setup phase; entrypoint drops to non-root after IP configuration)
- [x] Write `.dockerignore` (exclude tests, docs, .git, __pycache__)
- [x] Write `docker-compose.yml` for local development and testing
- [x] Write CI workflow (`ci.yml`): lint, test, build image, publish to `ghcr.io/rise-building-technology/bacnet-sim-ci`
- [x] Configure image tagging: semver on tags (`v1.0.0`), `latest` on main, SHA on every push
- [x] Handle SIGTERM gracefully: trap signal, close BAC0 instances, exit cleanly
- [x] Test: build image, run container, verify health check, verify BACnet and HTTP endpoints from host
- [x] Add resource usage guidance to README (memory per device, recommended runner specs)

**Success criteria:** `docker run ghcr.io/rise-building-technology/bacnet-sim-ci:latest` starts simulator, passes health check, responds to BACnet and HTTP requests. CI pipeline publishes image on push to main.

### Phase 5: GitHub Action Wrapper

**Goal:** Reusable GitHub Action for easy consumption.

**Files to create:**

```
  action.yml               # GitHub Action metadata
  examples/
    workflow-service-container.yml
    workflow-action.yml
    workflow-multi-device.yml
```

**Tasks:**

- [x] Write `action.yml`: Docker container action referencing pre-built ghcr.io image
- [x] Define action inputs: `device-id`, `device-name`, `port`, `config-file`, `network-profile`, `api-port`
- [x] Define action outputs: `api-url`, `bacnet-port`
- [x] Write example workflows: service container usage, action usage, multi-device setup
- [ ] Test action in a separate repo to verify end-to-end consumer experience

**Success criteria:** A consumer can add `uses: rise-building-technology/bacnet-sim-ci@v1` to their workflow and have a working BACnet simulator.

### Phase 6: Documentation and Polish

**Goal:** Production-ready README, examples, and documentation for public release.

**Files to create/modify:**

```
  README.md
  CONTRIBUTING.md
  LICENSE                  # LGPL-3.0 (inherited from BAC0)
  CLAUDE.md                # AI assistant conventions
```

**Tasks:**

- [x] Write README: quick start, configuration reference, API reference, networking guide, limitations, examples
- [x] Document Docker networking limitations prominently: no UDP broadcast across ports, unicast-only in Docker bridge, use `/api/devices` for discovery
- [x] Document all env vars, YAML schema, and precedence rules
- [x] Write CONTRIBUTING.md with development setup instructions
- [x] Add LICENSE file (LGPL-3.0-or-later)
- [x] Create CLAUDE.md with project conventions for AI-assisted development
- [x] Add badges to README: CI status, Docker image size, latest version

**Success criteria:** A developer unfamiliar with the project can go from `docker pull` to running integration tests by following the README alone.

## Acceptance Criteria

### Functional Requirements

- [x] Default HVAC controller starts with zero config and responds to BACnet ReadProperty
- [x] Multi-device mode: 3+ devices start on virtual IPs (same port 47808) from a single YAML config
- [x] BACnet WriteProperty changes presentValue on commandable objects
- [x] HTTP API reads/writes all object types and values are consistent with BACnet reads
- [x] Health check endpoint returns `503` during startup, `200` when all devices are ready
- [x] `GET /api/devices` lists all running devices with their IPs
- [x] Network lag profiles produce measurable latency differences
- [x] `unreliable-link` profile causes occasional BACnet request timeouts
- [x] YAML config validation rejects duplicate device IDs and duplicate object names
- [x] Container exits cleanly on SIGTERM (no orphaned processes)

### Non-Functional Requirements

- [x] Container starts and passes health check within 30 seconds (single device)
- [x] Docker image size under 200MB
- [x] Container entrypoint runs IP setup as root, then drops to non-root for the application
- [x] Works on GitHub Actions ubuntu-latest runners
- [x] Python 3.11+ only (no legacy support needed)

### Quality Gates

- [x] Unit tests for config loading, validation, device creation, lag simulation
- [x] Integration tests verifying BACnet protocol responses (ReadProperty, WriteProperty, Who-Is)
- [x] API endpoint tests for all REST routes
- [x] CI pipeline passes (lint, test, build, publish)
- [x] README includes working quick-start example

## Dependencies & Prerequisites

| Dependency | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Runtime |
| BAC0 | Latest | BACnet device simulation |
| BACpypes3 | (via BAC0) | BACnet protocol stack |
| FastAPI | Latest | REST API |
| Uvicorn | Latest | ASGI server |
| Pydantic | v2 | Config validation |
| PyYAML | Latest | YAML config parsing |
| Docker | Latest | Containerization |

## Risk Analysis & Mitigation

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| Virtual IP conflict on Docker network | Device fails to start | Medium | Check IP availability before adding; fail fast with clear error; auto-assign avoids manual conflicts |
| NET_ADMIN capability not granted | Container fails to start | Medium | Clear error message in entrypoint; document requirement in README and action.yml |
| BAC0 breaking change | Simulator breaks on update | Medium | Pin BAC0 version in requirements.txt; test in CI |
| Async event loop deadlock (BAC0 + FastAPI) | Container hangs | Medium | Keep all handlers async; avoid blocking calls; add startup timeout |
| Large multi-device configs exhaust memory | OOM kill in CI | Low | Document resource requirements; test with 10+ devices |
| Docker network subnet too small for device count | IP allocation fails | Low | Validate device count against subnet size at startup; default /24 supports 253 devices |

## Known Limitations (v1)

Document these prominently in README:

1. **Requires `--cap-add=NET_ADMIN` (or privileged mode).** The container adds virtual IPs to its network interface at startup. This is a Linux kernel capability (`CAP_NET_ADMIN`) that allows modifying network settings. Without it, multi-device mode cannot work.
2. **BACnet/IP only.** No MSTP (serial), no BACnet/SC.
3. **No COV subscriptions.** Change of Value notifications are not supported.
4. **No BBMD.** No BACnet Broadcast Management Device functionality.
5. **TrendLog is a static data container in v1.** It does not actively log values over time.
6. **Schedule does not drive output values in v1.** It stores schedule data but does not auto-update linked objects.
7. **Test client must be on the same Docker network.** BACnet/IP uses UDP broadcast for discovery. The client container/process must be on the same Docker network (or host network) as the simulator to send/receive BACnet traffic.

## References & Research

### Internal References

- Brainstorm: `docs/brainstorms/2026-02-15-bacnet-sim-ci-brainstorm.md`

### External References

- [BAC0 Documentation — Local Objects](https://bac0.readthedocs.io/en/latest/local_objects.html)
- [BAC0 GitHub — Multi-device issues](https://github.com/ChristianTremblay/BAC0/issues/358)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [GitHub Actions — Service Containers](https://docs.github.com/en/actions/using-containerized-services/about-service-containers)
- [GitHub Actions — Publishing Docker Images to GHCR](https://docs.github.com/en/actions/use-cases-and-examples/publishing-packages/publishing-docker-images)
- [Docker Best Practices for Python](https://testdriven.io/blog/docker-best-practices/)
