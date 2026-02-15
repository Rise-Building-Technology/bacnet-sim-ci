# CLAUDE.md

Project conventions for AI-assisted development.

## Project Overview

BACnet device simulator for CI pipelines. Uses BAC0 (BACpypes3) for BACnet/IP simulation, FastAPI for the REST API, and virtual IPs for multi-device support.

## Commands

```bash
# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/

# Auto-fix lint
ruff check --fix src/ tests/

# Build Docker image
docker build -t bacnet-sim-ci .

# Run locally (non-Docker, single device only)
python -m bacnet_sim.main
```

## Architecture

- **Config layer** (`config.py`, `defaults.py`): Pydantic models, YAML loading, env var overrides
- **Networking layer** (`networking.py`): Virtual IP allocation via `ip addr add` (Linux only)
- **Device layer** (`devices.py`): BAC0 device creation using factory pattern
- **Lag layer** (`lag.py`): Network delay/drop simulation per device
- **API layer** (`api.py`, `health.py`): FastAPI REST endpoints
- **Entry point** (`main.py`): Wires everything together in a single asyncio loop

## Key Patterns

- BAC0 factory functions (`analog_input`, `binary_output`, etc.) accumulate objects globally, then `add_objects_to_application(bacnet)` registers them all at once
- Each BAC0 device needs its own IP address (cannot share IP:port)
- Config loading priority: env vars > YAML > built-in defaults
- All async — FastAPI and BAC0 share one asyncio event loop via `uvicorn.Server.serve()`

## Testing

- Unit tests use mocked BAC0 objects (no real BACnet stack needed)
- FastAPI tests use `TestClient` with mock `SimulatedDevice` instances
- Integration tests (in `tests/test_integration.py`) require Docker and are skipped in local dev

## Constraints

- LGPL-3.0-or-later license (inherited from BAC0)
- Docker container requires `--cap-add=NET_ADMIN` for virtual IP setup
- Python 3.11+ only
