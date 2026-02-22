---
status: complete
priority: p1
issue_id: "001"
github_issue: 1
tags: [bug, lag, dead-code]
dependencies: []
---

# Lag simulation is dead code — never applied to BACnet responses

## Problem Statement
The lag simulation feature (`LagProfile.apply()`) is fully implemented and configurable via REST API and YAML config, but is never actually called anywhere. The README documents lag simulation as a working feature, but it's completely non-functional.

## Findings
- `LagProfile.apply()` exists in `src/bacnet_sim/lag.py` but no code ever calls it
- `SimulatedDevice.lag_profile` is set but never read during request handling
- `PUT /api/devices/{id}/network-profile` endpoint updates profile but nothing changes
- Location: `src/bacnet_sim/lag.py`, `src/bacnet_sim/devices.py`, `src/bacnet_sim/api.py`

## Proposed Solutions

### Option 1: Hook into BAC0 request handling
- **Pros**: Applies lag at the BACnet protocol level (realistic)
- **Cons**: Requires understanding BAC0 internals, may be complex
- **Effort**: Medium
- **Risk**: Medium

### Option 2: Wrap API-layer read/write with lag
- **Pros**: Simple to implement, works immediately
- **Cons**: Only affects REST API, not raw BACnet traffic
- **Effort**: Small
- **Risk**: Low

## Recommended Action
Start with Option 2 as a quick win, then investigate Option 1 for full BACnet-level lag.

## Technical Details
- **Affected Files**: `src/bacnet_sim/api.py`, `src/bacnet_sim/devices.py`
- **Related Components**: Lag profiles, API endpoints, device layer
- **Database Changes**: No

## Resources
- GitHub Issue: #1
- Related: lag.py already has full implementation and tests

## Acceptance Criteria
- [ ] `LagProfile.apply()` is called during BACnet object reads/writes
- [ ] Configuring `network_profile: unreliable-link` causes observable delays
- [ ] Packet drops return appropriate errors
- [ ] Tests pass
- [ ] Code reviewed

## Work Log

### 2026-02-22 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: **ready**
- P1 — this is a documented feature that is completely non-functional

## Notes
Source: Triage session on 2026-02-22
