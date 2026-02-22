---
status: complete
priority: p3
issue_id: "017"
github_issue: 17
tags: [enhancement, networking, cleanup]
dependencies: []
---

# Clean up virtual IPs for failed devices in start_devices

## Problem Statement
If `create_device()` fails for some devices, their virtual IPs remain allocated on the network interface but are never cleaned up.

## Findings
- Location: `src/bacnet_sim/main.py:62-74`
- Failed device IPs leak on the network interface
- Cleaned up only on container stop (minor in CI, worse in long-running scenarios)

## Proposed Solutions

### Option 1: Track and remove failed IPs
- **Pros**: Clean resource management
- **Cons**: Minimal added complexity
- **Effort**: Small
- **Risk**: Low

## Recommended Action
Collect failed device IPs in the error handler and call `remove_virtual_ip()` for each.

## Technical Details
- **Affected Files**: `src/bacnet_sim/main.py`
- **Database Changes**: No

## Resources
- GitHub Issue: #17

## Acceptance Criteria
- [ ] Failed device IPs are cleaned up
- [ ] Successful devices still work after partial failure
- [ ] Tests pass

## Work Log

### 2026-02-22 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: **ready**
- P3 — good hygiene, small fix

## Notes
Source: Triage session on 2026-02-22
