---
status: complete
priority: p3
issue_id: "022"
github_issue: 29
tags: [bug, api, memory]
dependencies: []
---

# Cap snapshot storage to prevent unbounded memory growth

## Problem Statement
The `snapshots` dict in `api.py:69` grows without bound. Each POST /api/snapshot adds an entry with full device state. No eviction, TTL, or max count.

## Findings
- Location: `src/bacnet_sim/api.py:69, 313-333`
- No limit on number of snapshots
- Each snapshot stores all object values for all devices
- Could exhaust memory in loops or long-running CI jobs

## Proposed Solutions

### Option 1: Cap at 100 snapshots, evict oldest
- **Pros**: Simple, safe default, no API change
- **Cons**: Silent eviction (could add warning log)
- **Effort**: Small (30 minutes)
- **Risk**: Low

## Recommended Action
Add MAX_SNAPSHOTS constant, evict oldest when full. Add DELETE endpoint for manual cleanup.

## Technical Details
- **Affected Files**: `src/bacnet_sim/api.py`
- **Database Changes**: No

## Acceptance Criteria
- [ ] Snapshots capped at reasonable limit
- [ ] Oldest evicted when full
- [ ] DELETE endpoint for cleanup
- [ ] Tests added

## Work Log

### 2026-02-25 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- GitHub Issue: #29

## Notes
Source: Triage session on 2026-02-25
