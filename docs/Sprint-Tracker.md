# Sprint Tracker

Track progress of the Horos modernization sprints. For detailed task checklists, see the [GitHub Issues](https://github.com/gerinsights/horos/issues).

## Phase 1: Foundation

| Sprint | Title | Issue | Effort | Status | Dependencies |
|--------|-------|-------|--------|--------|-------------|
| 0 | Build System & Toolchain | [#2](https://github.com/gerinsights/horos/issues/2) | 1 week | Not started | None |
| 1 | Safety Fixes & Security Deps | [#3](https://github.com/gerinsights/horos/issues/3) | 2 weeks | Not started | Sprint 0 |
| 2 | Remaining Dependency Updates | [#4](https://github.com/gerinsights/horos/issues/4) | 1-2 weeks | Not started | Sprint 1 |

## Phase 2: Rendering Migration

| Sprint | Title | Issue | Effort | Status | Dependencies |
|--------|-------|-------|--------|--------|-------------|
| 3 | VTK 8→9 Migration | [#5](https://github.com/gerinsights/horos/issues/5) | 3-4 weeks | Not started | Sprint 2 |
| 4 | DCMView OpenGL→Metal | [#6](https://github.com/gerinsights/horos/issues/6) | 4-6 weeks | Not started | Sprint 3 |
| 5 | ROI & CPR Metal Migration | [#7](https://github.com/gerinsights/horos/issues/7) | 2-3 weeks | Not started | Sprint 4 |
| 6 | Remove OpenGL Completely | [#8](https://github.com/gerinsights/horos/issues/8) | 1 week | Not started | Sprint 5 |

## Phase 3: Cleanup & Sustainability

| Sprint | Title | Issue | Effort | Status | Dependencies |
|--------|-------|-------|--------|--------|-------------|
| 7 | Deprecated API Cleanup | [#9](https://github.com/gerinsights/horos/issues/9) | 2-3 weeks | Not started | Sprint 0 (parallel with Phase 2) |
| 8 | Plugin SDK Modernization | [#10](https://github.com/gerinsights/horos/issues/10) | 2 weeks | Not started | Sprint 6 |
| 9 | Stabilization & Release | [#11](https://github.com/gerinsights/horos/issues/11) | 2-3 weeks | Not started | All prior |

## Dependency Graph

```
Sprint 0 ──┬── Sprint 1 ── Sprint 2 ── Sprint 3 ──┬── Sprint 4 ── Sprint 5 ── Sprint 6
            │                                       │
            └── Sprint 7 (parallel) ────────────────┘
                                                         Sprint 6 ── Sprint 8 ── Sprint 9
```

**Key parallelism:** Sprint 7 (deprecated APIs) is independent of Phase 2 rendering work.

## Total Estimated Effort

~20-30 weeks with parallelism on Sprint 7.
