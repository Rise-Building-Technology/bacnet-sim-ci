---
status: complete
priority: p3
issue_id: "019"
github_issue: 19
tags: [enhancement, networking, validation]
dependencies: []
---

# Detect IP overlap between explicit and auto-assigned IPs

## Problem Statement
No check that explicitly configured IPs don't collide with auto-computed IPs. A user with explicit `ip: 172.18.0.11` on device 2 could collide with auto-assigned IP for device 3.

## Findings
- Location: `src/bacnet_sim/networking.py:setup_virtual_ips()`
- `compute_virtual_ips()` doesn't know about explicit IPs
- Two devices could end up with the same IP

## Proposed Solutions

### Option 1: Post-assignment uniqueness check
- **Pros**: Simple, catches all collisions
- **Cons**: Fails late (after computing)
- **Effort**: Small
- **Risk**: Low

### Option 2: Pass explicit IPs to compute_virtual_ips to skip them
- **Pros**: Prevents collisions during assignment
- **Cons**: More refactoring
- **Effort**: Small-Medium
- **Risk**: Low

## Recommended Action
Option 1 as a quick check, optionally upgrade to Option 2.

## Technical Details
- **Affected Files**: `src/bacnet_sim/networking.py`
- **Database Changes**: No

## Resources
- GitHub Issue: #19

## Acceptance Criteria
- [ ] Overlapping IPs raise a clear error at startup
- [ ] Test validates collision detection
- [ ] Tests pass

## Work Log

### 2026-02-22 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: **ready**
- P3 — prevents a subtle multi-device misconfiguration

## Notes
Source: Triage session on 2026-02-22
