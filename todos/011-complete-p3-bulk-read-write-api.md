---
status: complete
priority: p3
issue_id: "011"
github_issue: 11
tags: [feature, api, bulk-operations]
dependencies: []
---

# Add bulk read/write API endpoints

## Problem Statement
The API only supports reading/writing one object at a time. CI test setup often needs to configure many values at once.

## Findings
- Location: `src/bacnet_sim/api.py`
- No batch endpoints exist
- Setting 20 objects requires 20 HTTP calls

## Proposed Solutions

### Option 1: Add POST bulk read/write endpoints
- **Pros**: Single HTTP call for batch operations, faster CI setup
- **Cons**: Slightly more API surface
- **Effort**: Small
- **Risk**: Low

## Recommended Action
Add `POST /api/devices/{id}/objects/read` and `POST /api/devices/{id}/objects/write` endpoints.

## Technical Details
- **Affected Files**: `src/bacnet_sim/api.py`
- **Database Changes**: No

## Resources
- GitHub Issue: #11

## Acceptance Criteria
- [ ] Bulk read accepts list of type/instance pairs, returns values
- [ ] Bulk write accepts list of type/instance/value, returns results
- [ ] Partial failures reported per-object (not all-or-nothing)
- [ ] Tests pass

## Work Log

### 2026-02-22 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: **ready**
- P3 — practical QoL improvement for CI users

## Notes
Source: Triage session on 2026-02-22
