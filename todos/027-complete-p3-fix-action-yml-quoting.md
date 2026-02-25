---
status: complete
priority: p3
issue_id: "027"
github_issue: 37
tags: [bug, ci, github-action]
dependencies: []
---

# Fix unquoted variable in action.yml docker run command

## Problem Statement
In `action.yml:87`, `$CONFIG_MOUNT` is unquoted in the `docker run` command. Paths with spaces cause word splitting and break the command.

## Findings
- Location: `action.yml:73-88`
- `CONFIG_MOUNT` string variable undergoes word splitting when unquoted
- Affects users with spaces in config file paths

## Proposed Solutions

### Option 1: Use bash array instead of string variable
- **Effort**: Small (15 minutes)
- **Risk**: Low

## Recommended Action
Replace string variable with bash array: `DOCKER_ARGS+=(-v ...)` and use `"${DOCKER_ARGS[@]}"`.

## Technical Details
- **Affected Files**: `action.yml`

## Acceptance Criteria
- [ ] Config mount uses bash array
- [ ] Works with paths containing spaces
- [ ] Existing action behavior unchanged

## Work Log

### 2026-02-25 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- GitHub Issue: #37

## Notes
Source: Triage session on 2026-02-25
