# Brainstorm: BACnet Device Simulator for GitHub CI

**Date:** 2026-02-15
**Status:** Draft

## What We're Building

A public, open-source BACnet device simulator designed to be pulled into GitHub CI pipelines for integration testing. It runs as a Docker container hosting one or more virtual BACnet/IP devices, each with configurable objects and initial values. Consumers can use it as:

1. **A GitHub Actions service container** — sidecar that runs alongside test jobs
2. **A reusable GitHub Action** — thin wrapper providing a clean input/output interface (`uses: org/bacnet-sim-ci@v1`)
3. **A standalone Docker image** — pulled from `ghcr.io` for local dev or other CI systems

The simulator supports the **extended BACnet object set** (Analog I/O, Binary I/O, Multistate Value, Character String, Schedule, Trend Log). Values can be changed two ways:

1. **BACnet WriteProperty** — simulated devices accept standard BACnet write requests over the protocol, behaving like real devices
2. **HTTP REST API** — for non-BACnet test orchestration (e.g., setting up scenarios from a test script)

The simulator also supports **network lag simulation** with configurable profiles:
- **local-network** — fast responses (0-10ms), no drops
- **remote-site** — moderate latency (50-200ms), rare timeouts
- **unreliable-link** — high latency (200-1000ms), occasional request drops/timeouts
- **custom** — user-defined min/max delay, timeout probability per device

## Why This Approach

**BAC0 as the BACnet engine:**
- High-level factory pattern for declaring objects in a few lines of code
- Built-in environment variable support (`BAC0_IP`, `BAC0_PORT`, etc.)
- Active development, built on BACpypes3
- Multi-device support via multiple BAC0 instances
- Tradeoff: LGPL license (acceptable for this project's goals)

**Docker image + GitHub Action (both):**
- Docker image is the core deliverable — works in any CI system, local dev, or Docker Compose
- GitHub Action wrapper adds convenience for the primary audience (GitHub Actions users)
- Service container pattern is ideal for long-running simulators that need to stay up for the duration of a test job

**YAML config + env var overrides:**
- YAML files define complex multi-device setups with full object definitions
- Environment variables override common settings (port, device ID) for simple cases
- Sensible defaults ship out of the box so it works with zero config

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| BACnet library | BAC0 | High-level API, fast development, env var support |
| License | LGPL (inherited from BAC0) | Acceptable for public simulator component |
| Delivery model | Docker image + GitHub Action | Maximum flexibility for consumers |
| Device topology | Multi-device per container | Supports testing device discovery and multi-device scenarios |
| Object types | Extended set | AI/AO, BI/BO, MSV, CharString, Schedule, TrendLog |
| Value mutation | BACnet WriteProperty + HTTP API | BACnet clients write via protocol; HTTP API for non-BACnet test orchestration |
| Configuration | YAML + env var overrides | Full expressiveness with simple-case convenience |
| Image registry | ghcr.io | Native to GitHub, free for public repos |
| Python version | 3.11+ | Required by BAC0/BACpypes3 |
| HTTP framework | FastAPI | Async-native, auto-generated OpenAPI docs |
| Default config | Generic HVAC controller | Zero-config experience with common BACnet points |
| GitHub org | rise-building-technology | Image at `ghcr.io/rise-building-technology/bacnet-sim-ci` |
| Network simulation | Configurable lag profiles | Presets (local/remote/unreliable) + custom delay/timeout settings per device |

## Scope

### In Scope (v1)
- Single Docker image with configurable multi-device BACnet simulator
- YAML-based device/object configuration
- Environment variable overrides for common settings
- HTTP REST API for reading/writing object values during tests
- Health check endpoint for container readiness
- GitHub Action wrapper (`action.yml`)
- Example workflows showing service container and action usage
- CI pipeline to build, test, and publish the image to ghcr.io
- README with usage docs and examples

### Out of Scope (for now)
- BACnet/MSTP (serial) — only BACnet/IP
- COV (Change of Value) subscriptions
- Simulation profiles (sine waves, random walks, schedule-based toggling)
- Web UI for interactive control
- BACnet security (BACnet/SC)
- BBMD functionality

## Resolved Questions

1. **HTTP API framework:** FastAPI — async-native (matches BAC0), auto-generates OpenAPI docs for discoverability.
2. **Default device config:** Generic HVAC controller — Zone Temp (AI), Setpoint (AO), Fan Status (BI), Fan Command (BO), Occupancy Mode (MSV), Status Text (CharStr). Works out of the box with zero config.
3. **Organization/namespace:** `rise-building-technology` — image path will be `ghcr.io/rise-building-technology/bacnet-sim-ci`.
