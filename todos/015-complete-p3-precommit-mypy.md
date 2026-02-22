---
status: complete
priority: p3
issue_id: "015"
tags: [dx, tooling, quality]
dependencies: []
---

# Add pre-commit hooks and mypy type checking

## Problem Statement
The project uses ruff for linting but lacks pre-commit hooks and static type checking. Type hints exist but are never validated.

## Findings
- Codebase uses type hints throughout but mypy is not configured
- No pre-commit hooks to catch issues before commit
- ruff format is not enforced

## Proposed Solutions

### Option 1: Add .pre-commit-config.yaml + mypy
- **Pros**: Catches type errors, enforces formatting, low friction
- **Cons**: Developers must install pre-commit
- **Effort**: Small
- **Risk**: Low

## Recommended Action
Add .pre-commit-config.yaml with ruff + ruff-format hooks. Add mypy to dev deps and CI. Configure mypy in pyproject.toml with BAC0 ignore.

## Technical Details
- **Affected Files**: `.pre-commit-config.yaml` (new), `pyproject.toml`, `.github/workflows/ci.yml`
- **Related Components**: CI pipeline, dev tooling

## Resources
- Original finding: GitHub Issue #15

## Acceptance Criteria
- [ ] .pre-commit-config.yaml created with ruff, ruff-format, standard hooks
- [ ] mypy configured in pyproject.toml with BAC0 import ignores
- [ ] mypy added to CI workflow
- [ ] All existing code passes mypy (or issues are typed: ignore'd)

## Work Log

### 2026-02-22 - Approved for Work
**By:** Triage System
**Actions:**
- Issue approved during triage session
- Status: ready

## Notes
Source: Triage session on 2026-02-22
