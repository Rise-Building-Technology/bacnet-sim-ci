---
status: complete
priority: p2
issue_id: "021"
github_issue: 28
tags: [bug, api, bacnet-fidelity]
dependencies: []
---

# Enforce commandable flag on write endpoint

## Problem Statement
The PUT write endpoint and bulk write endpoint allow writing to any object regardless of the `commandable` flag. Real BACnet returns `writeAccessDenied` for non-commandable objects. The simulator should enforce this for accurate test results.

## Findings
- Location: `src/bacnet_sim/api.py:167-202` (single write), `src/bacnet_sim/api.py:267-292` (bulk write)
- No check on `obj_config.commandable` before setting `presentValue`
- Analog-inputs (sensor readings) can be overwritten freely

## Proposed Solutions

### Option 1: Add commandable check with optional force override
- **Pros**: Accurate BACnet behavior, `?force=true` for test flexibility
- **Cons**: May break existing tests that write to non-commandable objects
- **Effort**: Small (1 hour)
- **Risk**: Low (add force param for backward compat)

## Recommended Action
Add commandable check to both write endpoints. Return 400 if not commandable. Add `?force=true` query param to bypass for test scenarios.

## Technical Details
- **Affected Files**: `src/bacnet_sim/api.py`
- **Related Components**: REST API write endpoints
- **Database Changes**: No

## Acceptance Criteria
- [ ] Write to non-commandable object returns 400
- [ ] `?force=true` bypasses the check
- [ ] Bulk write respects commandable per-object
- [ ] Tests updated for new behavior
- [ ] Existing tests pass

## Work Log

### 2026-02-25 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: ready
- GitHub Issue: #28

## Notes
Source: Triage session on 2026-02-25
