---
status: complete
priority: p3
issue_id: "018"
tags: [feature, ux, config]
dependencies: []
---

# Device templates / presets for common HVAC equipment

## Problem Statement
Users must manually define every object for each device in YAML. For common HVAC equipment (AHU, VAV, boiler, meter), built-in templates would reduce config boilerplate.

## Findings
- Current config requires listing all objects explicitly per device
- Common patterns repeat across projects (AHU objects, VAV objects, etc.)
- defaults.py already has a single default device — templates extend this concept

## Proposed Solutions

### Option 1: Template reference in device config
- **Pros**: Simple YAML syntax, extensible, allows overrides
- **Cons**: Need to maintain template definitions
- **Effort**: Medium
- **Risk**: Low

## Recommended Action
Add a `templates.py` with predefined object lists for ahu, vav, boiler, meter. Support `template: ahu` in device config YAML. Allow `objects:` to override/extend template objects.

## Technical Details
- **Affected Files**: `src/bacnet_sim/templates.py` (new), `src/bacnet_sim/config.py`, `src/bacnet_sim/defaults.py`
- **Related Components**: Config layer

## Resources
- Original finding: GitHub Issue #18

## Acceptance Criteria
- [ ] Templates for ahu, vav, boiler, meter defined
- [ ] `template:` key supported in device YAML config
- [ ] Template objects can be overridden/extended with explicit `objects:`
- [ ] Tests cover template loading and override behavior
- [ ] Documentation updated

## Work Log

### 2026-02-22 - Approved for Work
**By:** Triage System
**Actions:**
- Issue approved during triage session
- Status: ready

## Notes
Source: Triage session on 2026-02-22
