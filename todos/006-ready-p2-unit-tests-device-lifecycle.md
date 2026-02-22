---
status: ready
priority: p2
issue_id: "006"
github_issue: 6
tags: [enhancement, testing, coverage]
dependencies: []
---

# Add unit tests for create_device, shutdown_device, and main entry point

## Problem Statement
Several core functions have zero unit test coverage: `create_device()`, `shutdown_device()`, `start_devices()`, `main()`, and `setup_ips.main()`. These are the most critical code paths with no safety net.

## Findings
- `src/bacnet_sim/devices.py:130` — `create_device()` untested
- `src/bacnet_sim/devices.py:203` — `shutdown_device()` untested
- `src/bacnet_sim/main.py:36` — `start_devices()` untested
- `src/bacnet_sim/main.py:82` — `main()` untested
- `src/bacnet_sim/setup_ips.py:18` — standalone script untested

## Proposed Solutions

### Option 1: Add mocked unit tests for all functions
- **Pros**: Comprehensive coverage, catches regressions
- **Cons**: Requires mocking BAC0 internals
- **Effort**: Medium
- **Risk**: Low

## Recommended Action
Add test files with mocked BAC0 for device lifecycle functions. Priority: create_device > shutdown_device > start_devices.

## Technical Details
- **Affected Files**: New `tests/test_devices.py`, `tests/test_main.py`
- **Database Changes**: No

## Resources
- GitHub Issue: #6

## Acceptance Criteria
- [ ] `create_device()` tested with mocked BAC0
- [ ] `shutdown_device()` tested (success + error paths)
- [ ] `start_devices()` tested (partial failure path)
- [ ] Tests pass

## Work Log

### 2026-02-22 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: **ready**
- P2 — critical code paths need test coverage

## Notes
Source: Triage session on 2026-02-22
