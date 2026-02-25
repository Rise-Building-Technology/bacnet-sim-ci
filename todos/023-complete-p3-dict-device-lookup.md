---
status: complete
priority: p3
issue_id: "023"
github_issue: 30
tags: [enhancement, api, performance]
dependencies: []
---

# Use dict for device lookup instead of linear scan

## Problem Statement
`_find_device()` in `api.py:84-88` iterates the full device list on every request. Trivial to replace with O(1) dict lookup.

## Findings
- Location: `src/bacnet_sim/api.py:84-88`
- Called on nearly every API endpoint
- Easy 5-line change

## Proposed Solutions

### Option 1: Replace with dict comprehension
- **Effort**: Small (10 minutes)
- **Risk**: Low

## Recommended Action
Build `device_map = {d.device_id: d for d in devices}` in `create_app()`, use `.get()` in `_find_device()`.

## Technical Details
- **Affected Files**: `src/bacnet_sim/api.py`

## Acceptance Criteria
- [ ] Device lookup uses dict
- [ ] All existing tests pass
- [ ] No behavior change

## Work Log

### 2026-02-25 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- GitHub Issue: #30

## Notes
Source: Triage session on 2026-02-25
