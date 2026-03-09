# Design Decisions

Architectural decisions for the gerinsights/horos modernization. Updated as decisions are made.

## Decided

| # | Decision | Choice | Date | Rationale |
|---|----------|--------|------|-----------|
| 1 | Grok submodule | **Remove** | 2026-03-08 | Consolidate on OpenJPEG for JPEG 2000. Grok is 8 years behind, redundant. |
| 2 | VTK target version | **9.6.0** | 2026-03-08 | Latest release, future-proof. Skip intermediate versions. Metal backend available in 9.4+. |
| 3 | Plugin backward compat | **Hard break** | 2026-03-08 | Plugins must adopt Metal rendering. No OpenGL compatibility shim. Rewrite all gerinsights/horosplugins. |
| 4 | Fork stance | **Forward-only** | 2026-03-08 | Not backport-capable to horosproject/horos. Independent maintainable fork. |
| 5 | Deployment target | **macOS 14.0 (Sonoma)** | 2026-03-08 | Oldest Apple-supported release. Provides Metal 3, Swift concurrency runtime, modern AppKit. |
| 6 | C++ standard | **C++17** | 2026-03-08 | Required by CharLS 2.4+, ITK 6, modern DCMTK. Backward-compatible with existing code. |
| 7 | Metal approach | **Direct Metal rewrite** | 2026-03-08 | No compatibility layer. Custom MTKView subclass replacing NSOpenGLView. |

## To Be Decided

| # | Decision | Options | Sprint | Notes |
|---|----------|---------|--------|-------|
| 1 | FeedbackReporter | Remove / fork inline / replace with macOS crash reporter | Sprint 2 | Unmaintained since 2010 |
| 2 | Metal view base | Custom MTKView vs CAMetalLayer | Sprint 4 | Impacts all 2D rendering |
| 3 | Version numbering | Continue Horos 4.x / jump to 5.0 | Sprint 9 | Signals fork's major revision |
| 4 | Swift introduction | Pure ObjC / gradual Swift adoption | — | Currently zero Swift |
| 5 | ITK version | 5.4.5 (stable) / 6.0 (requires C++17, drops Intel) | Sprint 2 | ITK 6 is beta |

## Decision Template

When making a new decision, add it to the "Decided" table with:
- Sequential number
- Clear description of what was decided
- The choice made
- Date
- Brief rationale

Move it from "To Be Decided" if it was listed there.
