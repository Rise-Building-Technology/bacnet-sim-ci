---
status: complete
priority: p1
issue_id: "002"
github_issue: 2
tags: [bug, bac0, multi-device, state-leak]
dependencies: []
---

# BAC0 factory shared state may leak objects between devices

## Problem Statement
BAC0 factory functions accumulate objects in a class-level shared dict. When `create_device()` is called sequentially for multiple devices, objects from device 1 may still be in the shared accumulator when device 2 calls `add_objects_to_application()`.

## Findings
- `_create_object()` calls BAC0 factory functions that use shared class-level state
- `add_objects_to_application(bacnet)` registers ALL accumulated objects
- No explicit clearing of the accumulator between device creations
- Location: `src/bacnet_sim/devices.py:174-185`

## Proposed Solutions

### Option 1: Verify and clear BAC0 factory state
- **Pros**: Directly addresses the root cause
- **Cons**: Depends on BAC0 internals
- **Effort**: Small
- **Risk**: Low

## Recommended Action
Investigate BAC0's `add_objects_to_application()` to determine if it clears state. If not, explicitly clear the factory's shared dict before each device creation. Add a multi-device unit test.

## Technical Details
- **Affected Files**: `src/bacnet_sim/devices.py`
- **Related Components**: BAC0 factory pattern, multi-device creation
- **Database Changes**: No

## Resources
- GitHub Issue: #2

## Acceptance Criteria
- [ ] BAC0 factory state behavior verified
- [ ] Objects are isolated between devices in multi-device mode
- [ ] Unit test validates object isolation across 2+ devices
- [ ] Tests pass
- [ ] Code reviewed

## Work Log

### 2026-02-22 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: **ready**
- P1 — could cause incorrect object assignments in multi-device deployments

## Notes
Source: Triage session on 2026-02-22
