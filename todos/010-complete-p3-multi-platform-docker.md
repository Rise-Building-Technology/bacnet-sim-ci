---
status: complete
priority: p3
issue_id: "010"
tags: [infrastructure, docker, ci]
dependencies: []
---

# Multi-platform Docker builds (ARM64 / Apple Silicon)

## Problem Statement
The Docker image is only built for linux/amd64. Developers on Apple Silicon Macs or ARM-based CI runners must use emulation (slow) or cannot use the image at all.

## Findings
- BAC0 and BACpypes3 are pure Python — ARM64 should work without changes
- Base image `python:3.11-slim-bookworm` already supports ARM64
- System packages (iproute2, curl, gosu) available for ARM64 in Debian

## Proposed Solutions

### Option 1: QEMU + buildx in CI
- **Pros**: Standard approach, well-documented
- **Cons**: Slower builds due to emulation
- **Effort**: Small
- **Risk**: Low

## Recommended Action
Add docker/setup-qemu-action and docker/setup-buildx-action to CI, set platforms to linux/amd64,linux/arm64.

## Technical Details
- **Affected Files**: `.github/workflows/ci.yml`
- **Related Components**: Docker build pipeline

## Resources
- Original finding: GitHub Issue #10

## Acceptance Criteria
- [ ] Docker image builds for both amd64 and arm64
- [ ] CI workflow updated with QEMU and buildx
- [ ] Tests pass
- [ ] Image pushed to ghcr.io with multi-platform manifest

## Work Log

### 2026-02-22 - Approved for Work
**By:** Triage System
**Actions:**
- Issue approved during triage session
- Status: ready

## Notes
Source: Triage session on 2026-02-22
