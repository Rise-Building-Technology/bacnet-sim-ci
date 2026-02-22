---
status: complete
priority: p3
issue_id: "005"
github_issue: 5
tags: [enhancement, api, validation]
dependencies: []
---

# Validate object_type path parameter against ObjectType enum

## Problem Statement
API endpoints accept any string for `object_type` path parameter. Invalid types return a generic 404 instead of a helpful 422 validation error.

## Findings
- Location: `src/bacnet_sim/api.py` — read_object, write_object endpoints
- Invalid types like `foo` return "Object foo:1 not found" instead of "Invalid object type"

## Proposed Solutions

### Option 1: Use FastAPI Enum path parameter
- **Pros**: Automatic validation, OpenAPI docs, zero custom code
- **Cons**: None
- **Effort**: Small
- **Risk**: Low

## Recommended Action
Change `object_type: str` to `object_type: ObjectType` in API route signatures.

## Technical Details
- **Affected Files**: `src/bacnet_sim/api.py`
- **Database Changes**: No

## Resources
- GitHub Issue: #5

## Acceptance Criteria
- [ ] Invalid object types return 422 with valid types listed
- [ ] OpenAPI docs show valid enum values
- [ ] Existing tests updated
- [ ] Tests pass

## Work Log

### 2026-02-22 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: **ready**
- P3 — nice DX improvement, trivial to implement

## Notes
Source: Triage session on 2026-02-22
