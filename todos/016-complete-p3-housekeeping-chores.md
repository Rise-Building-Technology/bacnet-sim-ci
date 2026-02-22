---
status: complete
priority: p3
issue_id: "016"
github_issue: 16
tags: [chore, docker, dependencies]
dependencies: []
---

# Remove deprecated docker-compose version key and consolidate dependency files

## Problem Statement
`docker-compose.yml` has deprecated `version: "3.9"` key. Dependencies are duplicated in `pyproject.toml` and `requirements.txt` with no sync mechanism.

## Findings
- `docker-compose.yml` line 1 — deprecated `version` key
- `pyproject.toml` and `requirements.txt` list same 5 deps independently
- No mechanism to keep them in sync

## Proposed Solutions

### Option 1: Remove version key, use pip-compile for requirements.txt
- **Pros**: Clean, automated sync
- **Cons**: Adds pip-tools as dev dependency
- **Effort**: Small
- **Risk**: Low

## Recommended Action
Remove `version: "3.9"` from docker-compose.yml. Either generate requirements.txt from pyproject.toml or have Dockerfile use `pip install .` directly.

## Technical Details
- **Affected Files**: `docker-compose.yml`, `requirements.txt`, possibly `Dockerfile`
- **Database Changes**: No

## Resources
- GitHub Issue: #16

## Acceptance Criteria
- [ ] No deprecated version key in docker-compose.yml
- [ ] Single source of truth for dependencies
- [ ] Docker build still works
- [ ] Tests pass

## Work Log

### 2026-02-22 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: **ready**
- P3 — quick housekeeping

## Notes
Source: Triage session on 2026-02-22
