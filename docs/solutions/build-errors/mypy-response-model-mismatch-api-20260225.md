---
module: BACnet Simulator API
date: 2026-02-25
problem_type: build_error
component: tooling
symptoms:
  - "mypy: Incompatible return value type (got 'dict[Any, Any]', expected 'HealthResponse')"
  - "16 mypy errors in api.py after adding Pydantic response models"
  - "CI lint-and-test job failed on Type check with mypy step"
root_cause: logic_error
resolution_type: code_fix
severity: medium
tags: [mypy, fastapi, pydantic, response-model, type-checking, ci]
---

# Troubleshooting: mypy Fails When FastAPI Endpoints Use response_model With Dict Returns

## Problem
After adding Pydantic `response_model=` parameters to FastAPI endpoints for OpenAPI documentation, mypy reported 16 type errors because endpoints returned dict literals while their return type annotations declared Pydantic model types.

## Environment
- Module: BACnet Simulator API (`src/bacnet_sim/api.py`)
- Python Version: 3.11+
- FastAPI Version: >=0.110.0
- Pydantic Version: >=2.0.0
- Date: 2026-02-25

## Symptoms
- CI `lint-and-test` job failed at "Type check with mypy" step
- 16 errors of the form: `Incompatible return value type (got "dict[Any, Any]", expected "HealthResponse")`
- All errors in `src/bacnet_sim/api.py`
- Tests passed locally, ruff passed — only mypy failed

## What Didn't Work

**Direct solution:** The problem was identified and fixed on the first attempt after reading the CI logs.

## Solution

Changed return type annotations from Pydantic model types to `dict[str, Any]` while keeping `response_model=PydanticModel` on the decorator for OpenAPI documentation.

**Code changes:**

```python
# Before (broke mypy):
@app.get("/health/live", response_model=HealthResponse)
async def health_live() -> HealthResponse:
    return check_liveness()  # returns a dict, not HealthResponse

@app.get("/api/devices", response_model=list[DeviceSummary])
async def list_devices() -> list[DeviceSummary]:
    return [{"deviceId": d.device_id, ...} for d in devices]  # returns list[dict]

# After (mypy clean):
@app.get("/health/live", response_model=HealthResponse)
async def health_live() -> dict[str, Any]:
    return check_liveness()

@app.get("/api/devices", response_model=list[DeviceSummary])
async def list_devices() -> list[dict[str, Any]]:
    return [{"deviceId": d.device_id, ...} for d in devices]
```

Applied this pattern to all 16 endpoints that had the mismatch.

## Why This Works

1. **Root cause:** FastAPI's `response_model` parameter and the function's return type annotation serve different purposes. `response_model` controls OpenAPI schema generation and response serialization. The return type annotation is what mypy validates. When the function returns a `dict` but the annotation says `PydanticModel`, mypy correctly flags the mismatch.

2. **Why the fix works:** By annotating the return type as `dict[str, Any]` (matching what the function actually returns), mypy is satisfied. FastAPI still uses `response_model` for OpenAPI docs and will validate/serialize the dict through the Pydantic model at runtime.

3. **Key insight:** In FastAPI, `response_model` and the return type annotation are independent. You can return dicts from endpoints and FastAPI will coerce them through the response model. The return annotation should match the actual return value for mypy, not the desired serialization format.

## Prevention

- When adding `response_model=` to FastAPI endpoints, use `dict[str, Any]` or the appropriate dict type as the return annotation if the function returns dict literals
- Alternatively, return actual Pydantic model instances (e.g., `return HealthResponse(status="alive")`) to have both mypy and runtime type safety — but this requires more refactoring
- Run `mypy src/` locally before pushing when adding response models
- The project's `pyproject.toml` has `disallow_untyped_defs = true`, so return types cannot be omitted

## Related Issues

No related issues documented yet.
