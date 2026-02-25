---
status: complete
priority: p3
issue_id: "026"
github_issue: 33
tags: [enhancement, logging, debugging]
dependencies: []
---

# Replace bare except-pass blocks with logging

## Problem Statement
Four locations in `api.py` catch broad exceptions and silently discard them, making debugging difficult in CI environments.

## Findings
- `api.py:157-158` — statusFlags read silently dropped
- `api.py:308-310` — reset failures silently ignored
- `api.py:326-327` — snapshot read failures silently ignored
- `api.py:351-352` — restore failures silently ignored

## Proposed Solutions

### Option 1: Replace pass with logger.debug/warning, add error counts to responses
- **Effort**: Small (30 minutes)
- **Risk**: Low

## Recommended Action
Add logging to all four locations. For reset/restore, track and return error counts in the response body.

## Technical Details
- **Affected Files**: `src/bacnet_sim/api.py`

## Acceptance Criteria
- [ ] All bare except-pass replaced with logging
- [ ] Reset/restore responses include error counts
- [ ] Tests updated if response shape changes

## Work Log

### 2026-02-25 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- GitHub Issue: #33

## Notes
Source: Triage session on 2026-02-25
