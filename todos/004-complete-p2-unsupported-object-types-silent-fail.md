---
status: complete
priority: p2
issue_id: "004"
github_issue: 4
tags: [bug, config, validation]
dependencies: []
---

# SCHEDULE and TREND_LOG object types declared but not implemented

## Problem Statement
`ObjectType` enum includes `SCHEDULE` and `TREND_LOG`, but `OBJECT_FACTORIES` dict has no entries for them. Users can configure these in YAML and they're silently skipped at runtime.

## Findings
- `src/bacnet_sim/config.py` — enum declares SCHEDULE and TREND_LOG
- `src/bacnet_sim/devices.py` — OBJECT_FACTORIES missing these types
- Silent skip with warning log only

## Proposed Solutions

### Option 1: Remove from enum until implemented
- **Pros**: Prevents config-time confusion, clean enum
- **Cons**: Breaking change if anyone uses these values
- **Effort**: Small
- **Risk**: Low

### Option 2: Add config-time validation rejecting unsupported types
- **Pros**: Clear error message, keeps enum for future use
- **Cons**: Slightly more code
- **Effort**: Small
- **Risk**: Low

## Recommended Action
Option 2 — add a validator that checks object types against OBJECT_FACTORIES keys and raises a clear error.

## Technical Details
- **Affected Files**: `src/bacnet_sim/config.py` or `src/bacnet_sim/devices.py`
- **Database Changes**: No

## Resources
- GitHub Issue: #4
- Related: #22 (future implementation of these types)

## Acceptance Criteria
- [ ] Configuring unsupported object types produces a clear error at startup
- [ ] Tests validate the error message
- [ ] Tests pass

## Work Log

### 2026-02-22 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: **ready**
- P2 — silent failures are confusing for users

## Notes
Source: Triage session on 2026-02-22
