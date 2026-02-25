---
status: complete
priority: p3
issue_id: "024"
github_issue: 31
tags: [enhancement, api, documentation]
dependencies: []
---

# Add Pydantic response models for OpenAPI documentation

## Problem Statement
All API endpoints return raw `dict[str, Any]`, so auto-generated OpenAPI docs at `/docs` show no response schemas. Users must read source code to understand response shapes.

## Findings
- Location: `src/bacnet_sim/api.py` (all endpoint return types)
- FastAPI auto-generates docs from response models but has nothing to work with
- Important for a tool that CI pipelines integrate with

## Proposed Solutions

### Option 1: Add response model classes, use response_model parameter
- **Pros**: Auto docs, runtime validation, client codegen
- **Cons**: More code to maintain
- **Effort**: Medium (2-4 hours)
- **Risk**: Low

## Recommended Action
Add Pydantic models for DeviceSummary, ObjectDetail, WriteResponse, NetworkProfileResponse, etc. Apply via `response_model=` on each endpoint.

## Technical Details
- **Affected Files**: `src/bacnet_sim/api.py`

## Acceptance Criteria
- [ ] Response models for all endpoints
- [ ] `/docs` shows response schemas
- [ ] All existing tests pass

## Work Log

### 2026-02-25 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- GitHub Issue: #31

## Notes
Source: Triage session on 2026-02-25
