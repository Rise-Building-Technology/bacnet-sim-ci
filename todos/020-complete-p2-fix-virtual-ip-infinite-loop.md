---
status: complete
priority: p2
issue_id: "020"
github_issue: 27
tags: [bug, networking]
dependencies: []
---

# Fix compute_virtual_ips infinite-loop when subnet exhausted

## Problem Statement
In `networking.py:74-82`, the broadcast address guard uses `==` instead of `>=`. Once a candidate IP increments past the broadcast address, the loop spins forever until IPv4Address overflows with a confusing error.

## Findings
- Location: `src/bacnet_sim/networking.py:74-82`
- The guard `candidate == network.broadcast_address` only fires on exact match
- Once past broadcast, `candidate in network` is always False, no IPs appended, loop never exits
- Reproduces with: `compute_virtual_ips("192.168.1.1", 30, 10)`

## Proposed Solutions

### Option 1: Change guard to >= or check not-in-network
- **Pros**: Minimal change, clear error message
- **Cons**: None
- **Effort**: Small (15 minutes)
- **Risk**: Low

## Recommended Action
Change the guard condition and add a test for the edge case.

## Technical Details
- **Affected Files**: `src/bacnet_sim/networking.py`
- **Related Components**: Virtual IP allocation
- **Database Changes**: No

## Acceptance Criteria
- [ ] Guard catches candidates past broadcast address
- [ ] Clear "subnet too small" error message
- [ ] Unit test for edge case added
- [ ] Existing tests pass

## Work Log

### 2026-02-25 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: ready
- GitHub Issue: #27

## Notes
Source: Triage session on 2026-02-25
