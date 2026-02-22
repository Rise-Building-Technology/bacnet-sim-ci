---
status: complete
priority: p3
issue_id: "008"
github_issue: 8
tags: [feature, simulation, values]
dependencies: []
---

# Add value simulation / scripting support

## Problem Statement
BACnet object values are static unless explicitly written. For realistic CI testing, objects should support dynamic behavior like sine waves, random walks, and stepped values.

## Findings
- No simulation engine exists currently
- Values only change via REST API or BACnet WriteProperty
- Useful for testing timeout/retry and value-change detection logic

## Proposed Solutions

### Option 1: Async background tasks per simulated object
- **Pros**: Clean separation, per-object control
- **Cons**: More complex lifecycle management
- **Effort**: Large
- **Risk**: Medium

## Recommended Action
Implement sine, random-walk, and step modes as async tasks. Writing to a simulated object pauses the simulation.

## Technical Details
- **Affected Files**: New `src/bacnet_sim/simulation.py`, `src/bacnet_sim/config.py`, `src/bacnet_sim/api.py`
- **Database Changes**: No

## Resources
- GitHub Issue: #8

## Acceptance Criteria
- [ ] Sine wave mode works with configurable center/amplitude/period
- [ ] Random walk mode works with configurable bounds
- [ ] Step mode cycles through values
- [ ] Manual write pauses simulation
- [ ] API endpoint for simulation status
- [ ] Tests pass

## Work Log

### 2026-02-22 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: **ready**
- P3 — high value feature but large effort; nice differentiator

## Notes
Source: Triage session on 2026-02-22
