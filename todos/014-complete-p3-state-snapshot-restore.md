---
status: complete
priority: p3
issue_id: "014"
github_issue: 14
tags: [feature, api, state-management]
dependencies: []
---

# Add device state snapshot and restore

## Problem Statement
No way to save and restore device state between test cases. Tests that modify values can leak state into subsequent tests.

## Findings
- No snapshot/restore mechanism exists
- Container restart is the only way to reset state
- CI pipelines need test isolation

## Proposed Solutions

### Option 1: In-memory snapshot API with reset endpoint
- **Pros**: Simple, no persistence needed, covers the main use case
- **Cons**: Snapshots lost on container restart (acceptable for CI)
- **Effort**: Medium
- **Risk**: Low

## Recommended Action
Implement `POST /api/snapshot`, `POST /api/snapshot/{id}/restore`, and `POST /api/reset` endpoints. Start with reset-to-initial as the MVP.

## Technical Details
- **Affected Files**: `src/bacnet_sim/api.py`, possibly new `src/bacnet_sim/state.py`
- **Database Changes**: No

## Resources
- GitHub Issue: #14

## Acceptance Criteria
- [ ] `POST /api/reset` restores all objects to initial config values
- [ ] `POST /api/snapshot` saves current state
- [ ] `POST /api/snapshot/{id}/restore` restores saved state
- [ ] Tests pass

## Work Log

### 2026-02-22 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: **ready**
- P3 — valuable for CI test isolation

## Notes
Source: Triage session on 2026-02-22
