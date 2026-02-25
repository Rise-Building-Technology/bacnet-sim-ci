---
status: complete
priority: p2
issue_id: "025"
github_issue: 32
tags: [enhancement, testing]
dependencies: []
---

# Add test coverage for simulation API endpoints

## Problem Statement
The simulation engine has unit tests for `SimulationTask`, but the API endpoints (start/stop/status) and `SimulationManager` class have zero test coverage.

## Findings
- Location: `tests/test_api.py` (missing simulation tests), `tests/test_simulation.py` (missing manager tests)
- 3 untested endpoints: POST/DELETE/GET `.../simulate`
- `SimulationManager.start()`, `.stop()`, `.get()`, `.stop_all()` untested
- Write-stops-simulation behavior (`sim_manager.stop()` in `write_object`) untested

## Proposed Solutions

### Option 1: Add test classes for simulation endpoints and manager
- **Effort**: Medium (2-3 hours)
- **Risk**: Low

## Recommended Action
Add `TestSimulationEndpoints` class in `test_api.py` and `TestSimulationManager` class in `test_simulation.py`.

## Technical Details
- **Affected Files**: `tests/test_api.py`, `tests/test_simulation.py`

## Acceptance Criteria
- [ ] Tests for start/stop/status simulation endpoints
- [ ] Tests for SimulationManager methods
- [ ] Test that writing an object stops its active simulation
- [ ] Test for invalid simulation parameters
- [ ] All tests pass

## Work Log

### 2026-02-25 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- GitHub Issue: #32

## Notes
Source: Triage session on 2026-02-25
