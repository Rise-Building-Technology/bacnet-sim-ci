---
status: complete
priority: p2
issue_id: "003"
github_issue: 3
tags: [bug, config, defaults, units]
dependencies: []
---

# Default temperature values are Fahrenheit but units say Celsius

## Problem Statement
The default HVAC controller specifies temperature values like 72.5 and 55.0 with `unit: degreesCelsius`. These are clearly Fahrenheit values (72.5°C = 162.5°F).

## Findings
- `src/bacnet_sim/defaults.py` lines 26, 34, 40 — values 72.5, 55.0, 72.0 with degreesCelsius
- `config/default.yaml` lines 15, 20, 26 — same mismatch
- `config/example-multi-device.yaml` — similar values

## Proposed Solutions

### Option 1: Change units to degreesFahrenheit (Recommended)
- **Pros**: Preserves recognizable US-market HVAC values
- **Cons**: None
- **Effort**: Small
- **Risk**: Low

## Recommended Action
Change units to `degreesFahrenheit` in defaults.py, default.yaml, and example-multi-device.yaml.

## Technical Details
- **Affected Files**: `src/bacnet_sim/defaults.py`, `config/default.yaml`, `config/example-multi-device.yaml`, `README.md`
- **Database Changes**: No

## Resources
- GitHub Issue: #3

## Acceptance Criteria
- [ ] Temperature units match their numeric values across all config files
- [ ] README examples updated
- [ ] Tests pass

## Work Log

### 2026-02-22 - Approved for Work
**By:** Claude Triage System
**Actions:**
- Issue approved during triage session
- Status: **ready**
- P2 — misleading defaults, easy fix

## Notes
Source: Triage session on 2026-02-22
