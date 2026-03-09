# Horos Apple Silicon Modernization — Sprint Plan

**Date:** 2026-03-08
**Fork:** gerinsights/horos (not backport-capable to horosproject/horos)
**Goal:** Native Apple Silicon, current-gen macOS, maintainable long-term

---

## Executive Summary

Horos is a 339-file Objective-C/C++ medical imaging application with zero Swift, zero Metal, 1,065+ OpenGL references across 70+ files, and 9 submodules pinned 2–10 years behind current releases. VTK is at 8.2.0 (January 2019), requiring a full major-version migration to 9.x for Metal support. The codebase already compiles for arm64 but targets macOS 11.0 (EOL) with C++11.

This plan organizes modernization into 10 sprints across 3 phases, ordered to maintain a buildable/testable application at every sprint boundary.

### Codebase Metrics

| Metric | Value |
|--------|-------|
| Source files (Horos/Sources) | 339 .m/.mm |
| Swift files | 0 |
| OpenGL references | 1,065+ across 70+ files |
| Metal references | 0 |
| Largest files | ViewerController.m (22,872 lines), BrowserController.m (20,737 lines) |
| Submodules | 9, all outdated (2–10 years behind) |
| Deployment target | macOS 11.0 (EOL Sep 2023) |
| C++ standard | C++11 |
| Plugin format | .horosplugin / .osirixplugin (NSBundle dynamic loading) |

### Critical Path

```
CoreData (DicomStudy/Series/Image)
  → DICOM Parsing (DCM Framework + DCMTK)
    → Pixel Buffer (DCMPix)
      → 2D Rendering (DCMView — OpenGL)
      → 3D Rendering (VRView/MPRDCMView — VTK + OpenGL)
  → DICOM Network (DCMTK C-STORE/C-FIND/C-MOVE)
```

---

## Phase 1: Foundation (Sprints 0–2)

*Goal: Modern toolchain, safe concurrency, updated dependencies — without touching rendering.*

---

### Sprint 0 — Build System & Toolchain Modernization

**Objective:** Establish a clean, modern build foundation. Everything after this sprint builds on current-gen tooling.

#### 0.1 Raise deployment target
- [ ] Change `MACOSX_DEPLOYMENT_TARGET` from `11.0` to `14.0` (Sonoma)
  - File: `Config.xcconfig`
  - Rationale: macOS 14 is the oldest Apple-supported release. Provides Metal 3, Swift concurrency runtime, modern AppKit.
  - Enables `#available` guards for 14+ APIs throughout the migration

#### 0.2 Upgrade C++ standard
- [ ] Change `CLANG_CXX_LANGUAGE_STANDARD` from `c++0x` to `c++17` in project settings
- [ ] Update all CMake scripts to pass `-DCMAKE_CXX_STANDARD=17`
  - Files: `Horos/Scripts/{DCMTK,ITK,VTK,OpenJPEG,CharLS,GDCM,Grok}/CMake.sh`
- [ ] Fix any C++17 compilation errors (unlikely to be many — C++17 is backward-compatible)
- [ ] Rationale: CharLS 2.4+, ITK 6, and modern DCMTK all require C++17

#### 0.3 Clean legacy architecture references
- [ ] Remove `ppc`, `i386` from Nitrogen.xcodeproj ARCHS settings
- [ ] Remove `ppc`, `i386` from cocoahttpserver ARCHS settings
- [ ] Remove `ARCHS_STANDARD_32_64_BIT_PRE_XCODE_3_1` references
- [ ] Clean `altivecFunctions.h/c`: remove `#if __ppc__ || __ppc64__` branches (dead code)

#### 0.4 Remove dead code
- [ ] Remove `finalize` method implementations (5+ files — GC is dead since macOS 10.8)
  - Files: AppController.m, DCMView.m, DICOMExport.mm, ViewerController.m, WebPortal.mm
- [ ] Remove iChat/InstantMessage references (IChatTheatreDelegate.h/m, DCMView.h references)
  - iChat removed in macOS 10.8 — this code has been dead for 13 years
- [ ] Remove `#pragma clang diagnostic ignored` blocks for deprecated APIs (don't suppress — fix)

#### 0.5 Entitlements & hardened runtime
- [ ] Populate `Horos.entitlements` with required entitlements:
  - `com.apple.security.cs.disable-library-validation` (for plugin loading)
  - `com.apple.security.cs.allow-unsigned-executable-memory` (for VTK/OpenGL JIT if needed)
  - `com.apple.security.network.client` / `.server` (DICOM networking)
  - `com.apple.security.files.user-selected.read-write` (file access)
- [ ] Validate code signing works with hardened runtime

#### 0.6 CI/CD foundation
- [ ] Set up GitHub Actions or similar for the gerinsights/horos fork
- [ ] Build matrix: arm64 only (no universal binary needed for this fork)
- [ ] Ensure `xcodebuild -scheme Horos -arch arm64` succeeds as the gate

**Exit criteria:** Project builds cleanly on macOS 14 SDK, C++17, arm64-only, no legacy arch warnings.

---

### Sprint 1 — Safety Fixes & Security Dependencies

**Objective:** Fix thread-safety bugs and update security-critical libraries.

#### 1.1 Replace OSSpinLock with os_unfair_lock (HIGH — thread safety bug)
- [ ] Replace in all 7 files:
  - `N3BezierCore.m`
  - `WADODownload.m`
  - `DCMTKQueryNode.mm`
  - `CPRVolumeData.m`
  - `CPRStretchedOperation.m`
  - `CPRStraightenedOperation.m`
  - `CPRObliqueSliceOperation.m`
- [ ] Pattern: `#include <os/lock.h>`, replace `OSSpinLock` → `os_unfair_lock`, `OSSpinLockLock` → `os_unfair_lock_lock`, etc.
- [ ] Note: os_unfair_lock is not reentrant — verify no recursive locking patterns exist

#### 1.2 Update OpenSSL (3.0.4 → 3.6.x)
- [ ] Update submodule pointer: `git -C Horos/Submodules/OpenSSL checkout openssl-3.6.1`
- [ ] Update `Horos/Scripts/OpenSSL/Config.sh` if configure flags changed
- [ ] Run OpenSSL test suite
- [ ] Verify DICOM TLS connections still work (QueryController, WADO)
- [ ] Rationale: Multiple CVEs fixed since 3.0.4; 3.0 LTS EOL Sep 2026

#### 1.3 Update DCMTK (~3.6.7 → 3.7.0)
- [ ] Update submodule pointer
- [ ] Update `Horos/Scripts/DCMTK/CMake.sh` for any new CMake variables
- [ ] Fix compilation issues — DCMTK 3.7 API changes are typically minor
- [ ] Test: DICOM import, C-STORE SCP, C-FIND/C-MOVE SCU, print
- [ ] Key files affected: all `DCMTK*` classes, `OsiriXSCPDataHandler`, `BrowserControllerDCMTKCategory`

#### 1.4 Update GDCM (~3.0 → 3.2.2)
- [ ] Update submodule pointer
- [ ] Update CMake script
- [ ] GDCM is used for DICOM pixel data decompression — test JPEG/JPEG2000/JPEGLS decode
- [ ] Addresses CISA advisory for out-of-bounds write vulnerability

#### 1.5 Fix deprecated Security framework APIs
- [ ] Replace `SecPolicySearchCreate`/`SecPolicySearchCopyNext` in `cocoahttpserver/DDKeychain.m`
- [ ] Replace `SecKeychainFindGenericPassword` in `CSMailMailClient.m`
- [ ] Use modern SecKey/SecPolicy APIs

**Exit criteria:** No known thread-safety bugs. OpenSSL, DCMTK, GDCM at current versions. DICOM import/export/network verified working.

---

### Sprint 2 — Remaining Dependency Updates (Non-Rendering)

**Objective:** Update all non-VTK submodules. VTK is deferred to Sprint 3 because the 8→9 migration is massive and intertwined with the rendering pipeline.

#### 2.1 Update ITK (~5.2.1 → 5.4.5)
- [ ] Update submodule pointer
- [ ] Update `Horos/Scripts/ITK/CMake.sh`
- [ ] ITK 5.2→5.4 is a minor version bump — API changes should be manageable
- [ ] Test: image filtering, segmentation operations (ITKSegmentation3DController)
- [ ] Do NOT jump to ITK 6 yet (requires deeper C++17 refactoring of consumer code)

#### 2.2 Update OpenJPEG (~2.5.0 → 2.5.4)
- [ ] Update submodule pointer
- [ ] Bugfix release — should be drop-in compatible
- [ ] Test: JPEG 2000 DICOM decode/encode

#### 2.3 Update CharLS (2.0.0 → 2.4.3)
- [ ] Update submodule pointer
- [ ] **Breaking change**: CharLS 2.x→2.4 API may have changed; check `JpegLsReadHeader`/`JpegLsDecode` signatures
- [ ] Requires C++17 (done in Sprint 0)
- [ ] Test: JPEG-LS DICOM decode

#### 2.4 Evaluate Grok (untagged 2018 → 20.0.5)
- [ ] **Decision point**: Grok has an 8-year version gap. Options:
  - A) Update to 20.0.5 (may require significant API migration)
  - B) Remove Grok entirely and rely on OpenJPEG for JPEG 2000
  - C) Pin to a known-good intermediate version
- [ ] If keeping: update submodule and CMake script
- [ ] Test: JPEG 2000 Part 2 (HTJ2K) if applicable

#### 2.5 Evaluate FeedbackReporter
- [ ] Repository effectively unmaintained (last tag 2010)
- [ ] Options:
  - A) Remove and replace with modern crash reporting (e.g., built-in macOS crash reporter)
  - B) Fork the embedded code into the main project
  - C) Leave as-is (lowest effort, but carries maintenance debt)

**Exit criteria:** All non-VTK submodules at current versions. All DICOM codecs verified working. Build succeeds.

---

## Phase 2: Rendering Migration (Sprints 3–6)

*Goal: Migrate from OpenGL to Metal via VTK 9 + targeted Metal rewrites.*

---

### Sprint 3 — VTK 8.2.0 → 9.x Migration

**Objective:** The single largest dependency migration. VTK 9 has significant API changes from VTK 8 and adds Metal rendering backend support. This sprint focuses on getting VTK 9 compiling and the 3D views functional.

#### 3.1 Understand the VTK 8→9 API changes
- [ ] Key breaking changes to address:
  - `vtkSmartPointer` and `vtkNew` usage patterns
  - Removed `vtkRenderingOpenGL` module → `vtkRenderingOpenGL2`
  - Pipeline changes in volume rendering (vtkFixedPointVolumeRayCastMapper may be deprecated)
  - CMake module reorganization
  - C++17 requirement for VTK 9.4+

#### 3.2 Update VTK submodule and build
- [ ] Update submodule pointer to v9.4.x (latest with Metal support) or v9.6.0
- [ ] Rewrite `Horos/Scripts/VTK/CMake.sh`:
  - Enable Metal rendering backend: `-DVTK_DEFAULT_RENDER_WINDOW_OFFSCREEN=OFF`
  - Set module selections appropriate for medical imaging
  - Disable unused VTK modules to reduce build time
- [ ] Get VTK itself to compile for arm64 + macOS 14

#### 3.3 Migrate VRView (Volume Rendering)
- [ ] File: `Horos/Sources/VRView.mm` + `VRView+StereoVision.mm`
- [ ] Update VTK class references:
  - vtkFixedPointVolumeRayCastMapper → check if still available or use vtkGPUVolumeRayCastMapper
  - vtkVolumeTextureMapper* → vtkSmartVolumeMapper
  - Update pipeline connections
  - Clipping planes, pickers, interactors
- [ ] `VRViewVPRO.mm` — may be entirely removable if using modern VTK GPU ray casting

#### 3.4 Migrate SRView (Surface Rendering)
- [ ] File: `Horos/Sources/SRView.mm` + `SRView+StereoVision.mm`
- [ ] Update VTK surface rendering pipeline
- [ ] vtkContourFilter, vtkPolyDataMapper — generally stable APIs

#### 3.5 Migrate ROIVolumeView
- [ ] File: `Horos/Sources/ROIVolumeView.mm`
- [ ] Update VTK 3D ROI rendering

#### 3.6 Migrate MPR views using VTK
- [ ] File: `Horos/Sources/MPR2DView.mm`
- [ ] Update VTK reslicing pipeline

#### 3.7 Migrate VRPresetPreview
- [ ] File: `Horos/Sources/VRPresetPreview.mm`
- [ ] Small VTK view — update render pipeline

**Exit criteria:** All 3D views (VR, SR, MPR, ROI Volume) render correctly using VTK 9. VTK's Metal backend is active on Apple Silicon. No VTK 8 API calls remain.

---

### Sprint 4 — 2D Rendering: DCMView Metal Migration

**Objective:** Migrate the core 2D DICOM viewer from raw OpenGL to Metal. This is the highest-impact rendering change — DCMView.m alone has 356 OpenGL references and is the view every user sees.

#### Strategy Decision

Two viable approaches:

**Option A: Direct Metal rewrite** — Replace NSOpenGLView with MTKView, rewrite draw calls as Metal render passes. More work upfront, cleanest result, best long-term performance.

**Option B: CAOpenGLLayer bridge** — Use Apple's compatibility layer to run existing OpenGL code on Metal. Fastest to implement, but still deprecated and may have performance/compatibility issues.

**Recommended: Option A** — Direct Metal. This is a fork that doesn't need backward compatibility. A clean Metal implementation will be faster on Apple Silicon and eliminates the deprecation debt entirely.

#### 4.1 Create Metal rendering infrastructure
- [ ] Create `HorosMetalRenderer` — shared Metal device, command queue, pipeline state management
- [ ] Create `HorosMTKView` base class (subclass of MTKView) as replacement for NSOpenGLView subclasses
- [ ] Design texture upload pipeline: DCMPix float buffer → MTLTexture
- [ ] Implement window/level as a Metal fragment shader (currently done with OpenGL lookup tables)
- [ ] Implement CLUT (Color Lookup Table) as Metal 1D texture sampling

#### 4.2 Migrate DCMView core rendering
- [ ] File: `Horos/Sources/DCMView.m` (356 GL references — the biggest single file)
- [ ] Replace `NSOpenGLView` superclass with `HorosMTKView`
- [ ] Convert `drawRect:` from OpenGL immediate-mode to Metal render encoder:
  - Image quad rendering (textured rectangle)
  - Window/level adjustment (fragment shader)
  - Zoom/pan/rotate transforms (vertex shader uniform)
  - Overlay text rendering (StringTexture → Metal text rendering)
  - Crosshair/cursor rendering
- [ ] Remove all `gl*()` calls, `GL_*` constants, `CGLContextObj` references
- [ ] Preserve all tool interaction logic (mouse handling, gestures) — only change rendering backend

#### 4.3 Migrate StringTexture / GLString
- [ ] Files: `StringTexture.m/h`, `GLString.m/h`
- [ ] These render text labels as OpenGL textures
- [ ] Replace with Core Text → MTLTexture pipeline or use Metal-compatible text rendering
- [ ] Used by: DCMView, NavigatorView, ROI labels, measurement annotations

#### 4.4 Migrate OpenGLScreenReader
- [ ] File: `OpenGLScreenReader.m/h`
- [ ] Used for pixel readback (e.g., pixel value under cursor)
- [ ] Replace with MTLTexture readback (much simpler in Metal — just copy texture to CPU buffer)

#### 4.5 Migrate LoupeView
- [ ] File: `LoupeView.m` (57 GL references)
- [ ] Magnifying glass overlay — renders zoomed portion of image
- [ ] Convert to Metal texture sampling

#### 4.6 Migrate NavigatorView
- [ ] File: `NavigatorView.m` (70 GL references)
- [ ] Overview/thumbnail navigator
- [ ] Convert to Metal rendering

#### 4.7 Migrate PreviewView
- [ ] File: `PreviewView.m`
- [ ] Thumbnail preview rendering

**Exit criteria:** All 2D views render via Metal. Zero OpenGL calls in DCMView and related 2D view classes. Window/level, zoom, pan, rotate, annotations all working.

---

### Sprint 5 — ROI Rendering Migration

**Objective:** Migrate Region of Interest drawing from OpenGL to Metal. ROI.m has 201+ GL references and is tightly coupled to DCMView.

#### 5.1 ROI primitive rendering
- [ ] File: `ROI.m` (201+ GL references)
- [ ] Convert ROI drawing primitives to Metal:
  - Lines, polylines, polygons (glBegin/glEnd → Metal vertex buffers)
  - Filled regions (glPolygonMode → Metal pipeline state)
  - Text labels (GL string textures → Metal text)
  - Handles/control points (GL point rendering → Metal instanced rendering)
- [ ] ROI types to support: rectangle, ellipse, polygon, freehand, pencil, angle, arrow, text, measurement line, 2D point

#### 5.2 ROI interaction
- [ ] Hit testing (currently uses OpenGL selection/picking — convert to geometric calculation)
- [ ] Drag handles, resize, move operations
- [ ] ROI texture brushes/masks

#### 5.3 CPR views
- [ ] `CPRMPRDCMView.m` (81 GL references)
- [ ] `CPRStraightenedView.m` (66 GL references)
- [ ] `CPRStretchedView.m` (48 GL references)
- [ ] `CPRTransverseView.m`
- [ ] These are specialized 2D views for curved planar reconstruction — same migration pattern as DCMView

#### 5.4 Remaining 2D OpenGL views
- [ ] `OrthogonalMPRView.m`
- [ ] `MPRDCMView.m` (31 GL references)
- [ ] `EndoscopyMPRView.m`
- [ ] `LLScoutView.m`
- [ ] `CalciumScoringWindowController.m` (any embedded GL views)

**Exit criteria:** All ROI types render correctly on Metal. All CPR and specialized 2D views migrated. Total OpenGL reference count: zero in Horos/Sources.

---

### Sprint 6 — Remove OpenGL Completely

**Objective:** Eliminate all OpenGL framework references and verify Metal rendering end-to-end.

#### 6.1 Remove OpenGL framework dependency
- [ ] Remove `OpenGL.framework` from Xcode project link settings
- [ ] Remove all `#import <OpenGL/*>` includes
- [ ] Remove `CGLMacro.h` usage (14 files)
- [ ] Clean up any remaining GL utility code

#### 6.2 End-to-end rendering verification
- [ ] Test matrix:
  - 2D viewer: single image, series scroll, 4D cine, multi-frame
  - Window/level: all presets, custom W/L
  - All ROI types: create, edit, delete, copy/paste, import/export
  - MPR: orthogonal, oblique, CPR
  - Volume rendering: ray cast, MIP, shaded surface
  - Surface rendering: contour extraction, mesh display
  - Measurements: length, angle, area, SUV calculations
  - Annotations: text, arrows, key images
  - Export: screenshot, movie export, DICOM secondary capture

#### 6.3 Performance validation
- [ ] Compare rendering performance (Metal vs old OpenGL via Rosetta baseline if possible)
- [ ] Profile GPU utilization on Apple Silicon (M1/M2/M3)
- [ ] Check for frame drops during series scrolling and 3D rotation
- [ ] Verify memory usage is not significantly higher

**Exit criteria:** OpenGL.framework fully removed from the project. All rendering paths use Metal. Performance meets or exceeds OpenGL baseline.

---

## Phase 3: Cleanup & Sustainability (Sprints 7–9)

*Goal: Remove remaining deprecated APIs, modernize plugin SDK, establish maintainability.*

---

### Sprint 7 — Deprecated API Cleanup

**Objective:** Systematic removal of all deprecated macOS APIs.

#### 7.1 Carbon framework removal (6 files)
- [ ] `CSMailMailClient.m` — remove Carbon.h, use modern APIs for mail integration
- [ ] `Mailer.h` — remove Carbon dependency
- [ ] `OSIWindowController.m` — remove Carbon calls
- [ ] `OnOffSwitchControlCell.m` — rewrite without Carbon
- [ ] `Photos.h`, `Reports.h` — remove Carbon imports
- [ ] Replace `Gestalt()` calls with `NSProcessInfo.operatingSystemVersion` (3 files)
- [ ] Replace `FSRef`/`FSPathMakeRef` with NSURL-based file operations (7 files)

#### 7.2 QTKit → AVFoundation completion (12 files)
- [ ] `QuicktimeExport.m/h` — verify fully AVFoundation-based, rename methods
- [ ] Clean up all files referencing QTKit patterns:
  - CPRController.m, FlyThruController.mm, MPR2DController.mm, MPRController.m
  - SRView.mm, VRView.mm, VRViewVPRO.mm, ViewerController.m
- [ ] Replace `createMovieQTKit:` method names with `createMovie:` or `exportMovie:`

#### 7.3 NSCalendarDate → modern date APIs (42 files)
- [ ] This is the most widespread deprecated API usage
- [ ] Replace with `NSDateComponents` / `NSCalendar` / `NSDateFormatter`
- [ ] Bulk search-and-replace where patterns are consistent
- [ ] Special attention to DICOM date parsing (DA/TM/DT value representations)

#### 7.4 WebView → WKWebView (9 files)
- [ ] `PluginManagerController.m/h` — plugin download UI
- [ ] `SplashScreen.m/h` — startup screen
- [ ] `StructuredReportController.mm/h` — SR display
- [ ] `Decompress.mm` — decompression UI

#### 7.5 NSURLConnection → NSURLSession (2 files)
- [ ] `BrowserController.m`
- [ ] `WADODownload.m` — WADO download client

#### 7.6 Other deprecated APIs
- [ ] `stringWithCString:` → `stringWithCString:encoding:` (65 occurrences)
- [ ] `propertyListFromData:` → `propertyListWithData:options:format:error:` (8 files)
- [ ] `AddressBook` → `Contacts` framework (2-3 files)
- [ ] Replace vendored SBJSON with `NSJSONSerialization` (Nitrogen/Sources/JSON/)
- [ ] NSMatrix → NSCollectionView or NSStackView where practical (46 files — prioritize visible UI, defer internal usage)

**Exit criteria:** Zero deprecated API warnings when building with `-Wdeprecated-declarations` (without pragma suppression). All `#pragma clang diagnostic ignored` blocks for deprecations removed.

---

### Sprint 8 — Plugin SDK Modernization

**Objective:** Update the plugin architecture so gerinsights/horosplugins and third-party plugins can be modernized alongside the main app.

#### 8.1 Plugin SDK versioning
- [ ] Define `HOROS_PLUGIN_SDK_VERSION 5.0` (or appropriate version bump)
- [ ] Update `API/HorosAPI.m` version definitions
- [ ] Add SDK version check in `PluginManager.loadPluginBundle:` — warn on old SDK plugins

#### 8.2 Plugin rendering API
- [ ] The biggest breaking change: plugins that use OpenGL directly will break
- [ ] Provide a Metal-based rendering context for plugins:
  - New protocol method: `drawInMetalView:encoder:` (optional, alongside legacy `drawInOpenGLView:`)
  - During transition: provide a compatibility shim if feasible, or require plugin updates
- [ ] Update `PluginFilter.h` protocol:
  - Add `@optional` Metal rendering methods
  - Add `@optional` modern toolbar API methods (NSToolbarItemGroup)
  - Deprecate OpenGL-specific methods

#### 8.3 Plugin signature validation
- [ ] `isPluginBundleSignatureValid:` currently returns `YES` always
- [ ] Implement actual code signature validation using `SecStaticCode`
- [ ] Option: require Developer ID signing for plugins in hardened runtime mode

#### 8.4 gerinsights/horosplugins assessment
- [ ] When the horosplugins repo is accessible, audit each plugin for:
  - OpenGL usage (will need Metal migration)
  - Deprecated API usage
  - Architecture compatibility (arm64)
  - SDK version compatibility
- [ ] Create per-plugin migration checklist
- [ ] Expected common issues in plugins:
  - Direct OpenGL drawing in viewer overlays
  - NSCell/NSMatrix-based UIs
  - Carbon or QTKit dependencies
  - 32-bit type assumptions

#### 8.5 Plugin loading security
- [ ] Add `com.apple.security.cs.disable-library-validation` entitlement (Sprint 0)
- [ ] Test that unsigned plugins can still load in development
- [ ] Consider plugin sandboxing for future hardening

**Exit criteria:** Plugin SDK has clear versioning. Plugins can render via Metal. Plugin signature validation works. gerinsights/horosplugins audit complete with migration plan per plugin.

---

### Sprint 9 — Stabilization, Testing & Release Prep

**Objective:** Production-quality release of the modernized fork.

#### 9.1 Comprehensive testing
- [ ] DICOM conformance testing:
  - Import: CT, MR, US, XA, CR, DX, PT, NM, MG, SC, SR, PR, KO, SEG
  - All transfer syntaxes: Implicit VR LE, Explicit VR LE/BE, JPEG, JPEG2000, JPEG-LS, RLE
  - Multi-frame, enhanced multi-frame, color (RGB, YBR, palette)
  - 4D datasets (cardiac, dynamic contrast)
- [ ] PACS connectivity:
  - C-STORE SCP/SCU, C-FIND, C-MOVE, C-GET
  - WADO/DICOMweb (if supported)
  - TLS connections with updated OpenSSL
- [ ] Performance benchmarks:
  - Series loading time (100, 1000, 5000 images)
  - 3D volume rendering FPS (512³, 1024³ volumes)
  - MPR scroll performance
  - Database operations with 10K, 100K, 1M images
- [ ] Memory and GPU profiling on Apple Silicon

#### 9.2 CI/CD hardening
- [ ] Automated build on every PR
- [ ] Automated unit tests (add where missing for critical paths)
- [ ] DICOM test dataset in CI (anonymized samples per modality)
- [ ] Notarization pipeline for distribution

#### 9.3 Documentation
- [ ] FORK_DIFFERENCES.md — document all divergences from horosproject/horos
- [ ] PLUGIN_MIGRATION_GUIDE.md — guide for updating plugins to SDK 5.0 / Metal
- [ ] BUILD.md — updated build instructions for Apple Silicon
- [ ] Update embedded help and about screen

#### 9.4 Distribution
- [ ] Notarize with Apple
- [ ] Create DMG or installer package
- [ ] GitHub Releases on gerinsights/horos
- [ ] Tag as v5.0.0 (or appropriate version indicating the fork's major revision)

**Exit criteria:** All tests passing. Application notarized. Distribution package built. Documentation complete.

---

## Sprint Dependency Graph

```
Sprint 0 (Build System)
   │
   ├── Sprint 1 (Safety + Security Deps)
   │      │
   │      └── Sprint 2 (Remaining Deps)
   │             │
   │             └── Sprint 3 (VTK 8→9)
   │                    │
   │                    ├── Sprint 4 (2D Metal)
   │                    │      │
   │                    │      └── Sprint 5 (ROI Metal)
   │                    │             │
   │                    │             └── Sprint 6 (Remove OpenGL)
   │                    │
   │                    └─────────────────┐
   │                                      │
   └── Sprint 7 (Deprecated APIs) ◄───── can start after Sprint 0,
   │                                      parallel with Phase 2
   │
   └── Sprint 8 (Plugin SDK) ◄────────── requires Sprint 6 complete
          │
          └── Sprint 9 (Stabilization) ◄─ requires all prior sprints
```

**Key parallelism opportunity:** Sprint 7 (deprecated API cleanup) is largely independent of Phase 2 (rendering migration) and can be worked in parallel by a separate developer/workstream.

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| VTK 8→9 breaks 3D rendering pipeline | HIGH | HIGH | Budget extra time; VTK 9 migration guides exist. Consider intermediate step to 9.2 then 9.6. |
| OpenGL→Metal introduces visual regressions | HIGH | MEDIUM | Create screenshot comparison test suite before migration. Test every ROI type, every view mode. |
| CharLS 2.0→2.4 API incompatibility | MEDIUM | MEDIUM | If problematic, use GDCM's built-in CharLS for JPEG-LS decode instead. |
| Grok 2018→2026 migration infeasible | MEDIUM | HIGH | Fall back to OpenJPEG exclusively for JPEG 2000. |
| Plugin ecosystem breaks | MEDIUM | HIGH | Provide compatibility shim for one release cycle. Document migration path clearly. |
| ViewerController.m (22K lines) refactoring | MEDIUM | LOW | Don't refactor — only change rendering calls. Keep surgical. |
| DCMTK 3.7 network protocol changes | MEDIUM | LOW | DCMTK maintains strong backward compatibility. Test with known PACS systems. |
| Metal shader development time underestimated | HIGH | MEDIUM | Start with simplest possible shaders (textured quad + W/L). Add features incrementally. |

---

## Estimated Effort

| Sprint | Estimated Effort | Notes |
|--------|-----------------|-------|
| Sprint 0 | 1 week | Mostly configuration changes |
| Sprint 1 | 2 weeks | OpenSSL/DCMTK/GDCM updates + testing |
| Sprint 2 | 1–2 weeks | Remaining deps, Grok decision |
| Sprint 3 | 3–4 weeks | VTK 8→9 is the single hardest migration |
| Sprint 4 | 4–6 weeks | DCMView Metal rewrite is the largest volume of work |
| Sprint 5 | 2–3 weeks | ROI + CPR views |
| Sprint 6 | 1 week | Cleanup and verification |
| Sprint 7 | 2–3 weeks | Can run parallel with Phase 2 |
| Sprint 8 | 2 weeks | Plugin SDK + horosplugins audit |
| Sprint 9 | 2–3 weeks | Testing, CI, documentation |
| **Total** | **~20–30 weeks** | With parallelism on Sprint 7 |

---

## gerinsights/horosplugins — Anticipated Issues

Based on the plugin architecture analysis, plugins loaded via NSBundle will face these common modernization issues:

| Issue | Affected Plugins | Fix |
|-------|-----------------|-----|
| OpenGL drawing in viewer overlays | Any plugin using `drawInOpenGLView:` or direct GL calls | Migrate to Metal rendering API (Sprint 8) |
| NSCell/NSMatrix-based UI | Plugins with custom preference panels or tool palettes | Replace with NSCollectionView/NSStackView |
| Carbon framework dependencies | Plugins using Carbon events or file APIs | Replace with Cocoa equivalents |
| x86_64-only binaries | Pre-built plugins not compiled for arm64 | Recompile from source for arm64 |
| QTKit movie export | Plugins creating movies/animations | Migrate to AVFoundation |
| Old plugin SDK version | Plugins built against OsiriX-era SDK | Update to Horos SDK 5.0 |

**Recommendation:** After Sprint 8 establishes the new plugin SDK, create a separate sprint plan for horosplugins migration, plugin-by-plugin. Each plugin should be treated as a mini-project with its own build/test cycle.

---

## Decision Log

Decisions to be made during execution:

1. **Sprint 0:** Final deployment target — macOS 14.0 (Sonoma) vs 15.0 (Sequoia)?
2. **Sprint 2:** Grok — update, remove, or replace?
3. **Sprint 2:** FeedbackReporter — remove, fork, or replace?
4. **Sprint 3:** VTK target version — 9.4.x (proven Metal) vs 9.6.0 (latest)?
5. **Sprint 4:** Metal rendering approach — custom MTKView vs CAMetalLayer?
6. **Sprint 8:** Plugin backward compatibility — provide shim or hard break?
7. **Sprint 9:** Version numbering — continue Horos 4.x or jump to 5.0?
