#!/usr/bin/env bash
#
# GitHub Project Setup for Horos Modernization
#
# Usage: .github/setup-project.sh
#
# Prerequisites:
#   - gh CLI authenticated: `gh auth login`
#   - Repository: gerinsights/horos
#
# This script creates:
#   - Milestones (one per sprint phase)
#   - Labels for sprint tracking
#   - Issues for each sprint with full task checklists
#
set -euo pipefail

REPO="gerinsights/horos"

echo "=== Setting up GitHub project tracking for Horos Modernization ==="
echo "Repository: $REPO"
echo ""

# ─────────────────────────────────────────────
# Labels
# ─────────────────────────────────────────────
echo "Creating labels..."

declare -A LABELS=(
  ["sprint:0"]="Phase 1: Build System & Toolchain"
  ["sprint:1"]="Phase 1: Safety Fixes & Security Deps"
  ["sprint:2"]="Phase 1: Remaining Dependency Updates"
  ["sprint:3"]="Phase 2: VTK 8→9 Migration"
  ["sprint:4"]="Phase 2: 2D Metal Migration"
  ["sprint:5"]="Phase 2: ROI Metal Migration"
  ["sprint:6"]="Phase 2: Remove OpenGL"
  ["sprint:7"]="Phase 3: Deprecated API Cleanup"
  ["sprint:8"]="Phase 3: Plugin SDK Modernization"
  ["sprint:9"]="Phase 3: Stabilization & Release"
  ["priority:critical"]="Blocking or security-critical"
  ["priority:high"]="Important for next milestone"
  ["priority:medium"]="Should be done but not blocking"
  ["priority:low"]="Nice to have"
  ["type:dependency-update"]="Submodule or library update"
  ["type:migration"]="API migration (OpenGL→Metal, etc.)"
  ["type:cleanup"]="Dead code removal or deprecation fix"
  ["type:infrastructure"]="CI/CD, build system, toolchain"
  ["type:plugin"]="Plugin SDK or plugin migration"
  ["type:testing"]="Test coverage or verification"
  ["area:rendering"]="2D/3D rendering pipeline"
  ["area:dicom"]="DICOM parsing, network, or storage"
  ["area:ui"]="User interface components"
  ["area:build"]="Build system and dependencies"
)

declare -A LABEL_COLORS=(
  ["sprint:0"]="0E8A16" ["sprint:1"]="0E8A16" ["sprint:2"]="0E8A16"
  ["sprint:3"]="1D76DB" ["sprint:4"]="1D76DB" ["sprint:5"]="1D76DB" ["sprint:6"]="1D76DB"
  ["sprint:7"]="5319E7" ["sprint:8"]="5319E7" ["sprint:9"]="5319E7"
  ["priority:critical"]="B60205" ["priority:high"]="D93F0B"
  ["priority:medium"]="FBCA04" ["priority:low"]="C2E0C6"
  ["type:dependency-update"]="BFD4F2" ["type:migration"]="D4C5F9"
  ["type:cleanup"]="FEF2C0" ["type:infrastructure"]="C5DEF5"
  ["type:plugin"]="F9D0C4" ["type:testing"]="BFDADC"
  ["area:rendering"]="E99695" ["area:dicom"]="D4C5F9"
  ["area:ui"]="C2E0C6" ["area:build"]="C5DEF5"
)

for label in "${!LABELS[@]}"; do
  desc="${LABELS[$label]}"
  color="${LABEL_COLORS[$label]}"
  gh label create "$label" --description "$desc" --color "$color" --repo "$REPO" --force 2>/dev/null && \
    echo "  ✓ $label" || echo "  - $label (exists)"
done

echo ""

# ─────────────────────────────────────────────
# Milestones
# ─────────────────────────────────────────────
echo "Creating milestones..."

gh api repos/$REPO/milestones -X POST -f title="Phase 1: Foundation (Sprints 0-2)" \
  -f description="Modern toolchain, safe concurrency, updated dependencies. Build system (C++17, macOS 14), OSSpinLock fix, OpenSSL/DCMTK/GDCM/ITK/OpenJPEG/CharLS updates, Grok removal." \
  -f state="open" 2>/dev/null && echo "  ✓ Phase 1" || echo "  - Phase 1 (exists)"

gh api repos/$REPO/milestones -X POST -f title="Phase 2: Rendering Migration (Sprints 3-6)" \
  -f description="VTK 8.2→9.6 migration, OpenGL→Metal rewrite for all 2D/3D views. 1,065+ GL references across 70+ files." \
  -f state="open" 2>/dev/null && echo "  ✓ Phase 2" || echo "  - Phase 2 (exists)"

gh api repos/$REPO/milestones -X POST -f title="Phase 3: Cleanup & Sustainability (Sprints 7-9)" \
  -f description="Deprecated API removal, plugin SDK modernization (hard break), stabilization, testing, and release." \
  -f state="open" 2>/dev/null && echo "  ✓ Phase 3" || echo "  - Phase 3 (exists)"

echo ""

# Get milestone numbers
PHASE1=$(gh api repos/$REPO/milestones --jq '.[] | select(.title | startswith("Phase 1")) | .number' 2>/dev/null)
PHASE2=$(gh api repos/$REPO/milestones --jq '.[] | select(.title | startswith("Phase 2")) | .number' 2>/dev/null)
PHASE3=$(gh api repos/$REPO/milestones --jq '.[] | select(.title | startswith("Phase 3")) | .number' 2>/dev/null)

echo "Milestone numbers: Phase1=$PHASE1, Phase2=$PHASE2, Phase3=$PHASE3"
echo ""

# ─────────────────────────────────────────────
# Issues
# ─────────────────────────────────────────────
echo "Creating sprint issues..."

# Sprint 0
gh issue create --repo "$REPO" \
  --title "Sprint 0: Build System & Toolchain Modernization" \
  --milestone "Phase 1: Foundation (Sprints 0-2)" \
  --label "sprint:0,type:infrastructure,area:build,priority:critical" \
  --body "$(cat <<'ISSUE_EOF'
## Objective
Establish a clean, modern build foundation. Everything after this sprint builds on current-gen tooling.

## Tasks

### 0.1 Raise deployment target
- [ ] Change `MACOSX_DEPLOYMENT_TARGET` from `11.0` to `14.0` (Sonoma) in `Config.xcconfig`

### 0.2 Upgrade C++ standard
- [ ] Change `CLANG_CXX_LANGUAGE_STANDARD` from `c++0x` to `c++17` in project settings
- [ ] Update all CMake scripts to pass `-DCMAKE_CXX_STANDARD=17` (`Horos/Scripts/*/CMake.sh`)
- [ ] Fix any C++17 compilation errors

### 0.3 Clean legacy architecture references
- [ ] Remove `ppc`, `i386` from Nitrogen.xcodeproj ARCHS
- [ ] Remove `ppc`, `i386` from cocoahttpserver ARCHS
- [ ] Remove `ARCHS_STANDARD_32_64_BIT_PRE_XCODE_3_1` references
- [ ] Clean `altivecFunctions.h/c`: remove `#if __ppc__ || __ppc64__` branches

### 0.4 Remove dead code
- [ ] Remove `finalize` method implementations (5+ files — GC dead since macOS 10.8)
- [ ] Remove iChat/InstantMessage references (IChatTheatreDelegate.h/m)
- [ ] Remove `#pragma clang diagnostic ignored` blocks for deprecated APIs

### 0.5 Entitlements & hardened runtime
- [ ] Populate `Horos.entitlements` with required entitlements
- [ ] Validate code signing with hardened runtime

### 0.6 CI/CD foundation
- [ ] GitHub Actions workflow for arm64 builds ✅ (done in planning PR)
- [ ] Verify `xcodebuild -scheme Horos -arch arm64` succeeds

## Exit Criteria
Project builds cleanly on macOS 14 SDK, C++17, arm64-only, no legacy arch warnings.

## Estimated Effort
1 week

## Dependencies
None — this is the first sprint.
ISSUE_EOF
)" && echo "  ✓ Sprint 0" || echo "  ✗ Sprint 0 failed"

# Sprint 1
gh issue create --repo "$REPO" \
  --title "Sprint 1: Safety Fixes & Security Dependencies" \
  --milestone "Phase 1: Foundation (Sprints 0-2)" \
  --label "sprint:1,type:dependency-update,priority:critical" \
  --body "$(cat <<'ISSUE_EOF'
## Objective
Fix thread-safety bugs and update security-critical libraries.

## Tasks

### 1.1 Replace OSSpinLock with os_unfair_lock (thread safety bug)
- [ ] `N3BezierCore.m`
- [ ] `WADODownload.m`
- [ ] `DCMTKQueryNode.mm`
- [ ] `CPRVolumeData.m`
- [ ] `CPRStretchedOperation.m`
- [ ] `CPRStraightenedOperation.m`
- [ ] `CPRObliqueSliceOperation.m`
- [ ] Verify no recursive locking patterns (os_unfair_lock is not reentrant)

### 1.2 Update OpenSSL (3.0.4 → 3.6.x)
- [ ] Update submodule pointer
- [ ] Update `Horos/Scripts/OpenSSL/Config.sh` if needed
- [ ] Test DICOM TLS connections

### 1.3 Update DCMTK (~3.6.7 → 3.7.0)
- [ ] Update submodule pointer
- [ ] Update CMake script
- [ ] Test: DICOM import, C-STORE, C-FIND/C-MOVE, print

### 1.4 Update GDCM (~3.0 → 3.2.2)
- [ ] Update submodule pointer
- [ ] Test JPEG/JPEG2000/JPEGLS decode
- [ ] Addresses CISA advisory for OOB write vulnerability

### 1.5 Fix deprecated Security framework APIs
- [ ] Replace `SecPolicySearchCreate`/`SecPolicySearchCopyNext` in `cocoahttpserver/DDKeychain.m`
- [ ] Replace `SecKeychainFindGenericPassword` in `CSMailMailClient.m`

## Exit Criteria
No known thread-safety bugs. OpenSSL, DCMTK, GDCM at current versions. DICOM import/export/network verified.

## Estimated Effort
2 weeks

## Dependencies
- Sprint 0 (build system)
ISSUE_EOF
)" && echo "  ✓ Sprint 1" || echo "  ✗ Sprint 1 failed"

# Sprint 2
gh issue create --repo "$REPO" \
  --title "Sprint 2: Remaining Dependency Updates (Non-Rendering)" \
  --milestone "Phase 1: Foundation (Sprints 0-2)" \
  --label "sprint:2,type:dependency-update,priority:high" \
  --body "$(cat <<'ISSUE_EOF'
## Objective
Update all non-VTK submodules. VTK deferred to Sprint 3 (8→9 is massive).

## Tasks

### 2.1 Update ITK (~5.2.1 → 5.4.5)
- [ ] Update submodule pointer
- [ ] Update CMake script
- [ ] Test: image filtering, segmentation (ITKSegmentation3DController)

### 2.2 Update OpenJPEG (~2.5.0 → 2.5.4)
- [ ] Update submodule pointer (bugfix release, drop-in)
- [ ] Test: JPEG 2000 DICOM decode/encode

### 2.3 Update CharLS (2.0.0 → 2.4.3)
- [ ] Update submodule pointer
- [ ] Check API changes (`JpegLsReadHeader`/`JpegLsDecode` signatures)
- [ ] Test: JPEG-LS DICOM decode

### 2.4 Remove Grok submodule (DECIDED)
- [ ] `git submodule deinit Grok && git rm Grok`
- [ ] Remove `Horos/Scripts/Grok/` CMake scripts
- [ ] Remove Grok references from Xcode project
- [ ] Update code to use OpenJPEG exclusively for JPEG 2000
- [ ] Test: JPEG 2000 decode/encode with OpenJPEG only

### 2.5 Evaluate FeedbackReporter
- [ ] Decision: remove, fork inline, or replace with macOS crash reporter
- [ ] Implement chosen approach

## Exit Criteria
All non-VTK submodules at current versions. All DICOM codecs verified. Grok removed.

## Estimated Effort
1–2 weeks

## Dependencies
- Sprint 1 (safety fixes)
ISSUE_EOF
)" && echo "  ✓ Sprint 2" || echo "  ✗ Sprint 2 failed"

# Sprint 3
gh issue create --repo "$REPO" \
  --title "Sprint 3: VTK 8.2.0 → 9.6.0 Migration" \
  --milestone "Phase 2: Rendering Migration (Sprints 3-6)" \
  --label "sprint:3,type:migration,area:rendering,priority:critical" \
  --body "$(cat <<'ISSUE_EOF'
## Objective
The single largest dependency migration. VTK 9 has significant API changes from VTK 8 and adds Metal rendering backend.

**DECIDED: Target VTK v9.6.0** (latest, future-proof)

## Tasks

### 3.1 Understand VTK 8→9 API changes
- [ ] Document breaking changes: vtkSmartPointer patterns, module reorganization
- [ ] vtkRenderingOpenGL → vtkRenderingOpenGL2
- [ ] Volume rendering mapper changes
- [ ] C++17 requirement

### 3.2 Update VTK submodule and build
- [ ] Update submodule to v9.6.0
- [ ] Rewrite `Horos/Scripts/VTK/CMake.sh` (Metal backend, module selection)
- [ ] Get VTK compiling for arm64 + macOS 14

### 3.3 Migrate VRView (Volume Rendering)
- [ ] `VRView.mm` + `VRView+StereoVision.mm`
- [ ] Update VTK class references (mappers, pipeline, pickers)
- [ ] Evaluate removing `VRViewVPRO.mm` (may be redundant with modern VTK)

### 3.4 Migrate SRView (Surface Rendering)
- [ ] `SRView.mm` + `SRView+StereoVision.mm`

### 3.5 Migrate ROIVolumeView
- [ ] `ROIVolumeView.mm`

### 3.6 Migrate MPR views using VTK
- [ ] `MPR2DView.mm`

### 3.7 Migrate VRPresetPreview
- [ ] `VRPresetPreview.mm`

## Exit Criteria
All 3D views render correctly using VTK 9.6. VTK's Metal backend active on Apple Silicon. No VTK 8 API calls remain.

## Estimated Effort
3–4 weeks (single hardest migration)

## Dependencies
- Sprint 2 (dependency updates)
ISSUE_EOF
)" && echo "  ✓ Sprint 3" || echo "  ✗ Sprint 3 failed"

# Sprint 4
gh issue create --repo "$REPO" \
  --title "Sprint 4: 2D Rendering — DCMView OpenGL→Metal Migration" \
  --milestone "Phase 2: Rendering Migration (Sprints 3-6)" \
  --label "sprint:4,type:migration,area:rendering,priority:critical" \
  --body "$(cat <<'ISSUE_EOF'
## Objective
Migrate the core 2D DICOM viewer from raw OpenGL to Metal. DCMView.m has 356 OpenGL references — the highest-impact rendering change.

**Approach: Direct Metal rewrite** (no compatibility layer — this fork doesn't need backward compat)

## Tasks

### 4.1 Create Metal rendering infrastructure
- [ ] `HorosMetalRenderer` — shared Metal device, command queue, pipeline states
- [ ] `HorosMTKView` base class (MTKView subclass replacing NSOpenGLView)
- [ ] Texture upload: DCMPix float buffer → MTLTexture
- [ ] Window/level fragment shader
- [ ] CLUT as Metal 1D texture sampling

### 4.2 Migrate DCMView core rendering
- [ ] `DCMView.m` (356 GL references)
- [ ] Replace NSOpenGLView → HorosMTKView
- [ ] Convert drawRect: to Metal render encoder
- [ ] Image quad, W/L, zoom/pan/rotate, overlays, crosshairs

### 4.3 Migrate StringTexture / GLString
- [ ] `StringTexture.m/h`, `GLString.m/h` → Core Text + MTLTexture

### 4.4 Migrate OpenGLScreenReader
- [ ] `OpenGLScreenReader.m/h` → MTLTexture readback

### 4.5 Migrate LoupeView
- [ ] `LoupeView.m` (57 GL refs) → Metal magnifier

### 4.6 Migrate NavigatorView
- [ ] `NavigatorView.m` (70 GL refs) → Metal navigator

### 4.7 Migrate PreviewView
- [ ] `PreviewView.m` → Metal preview

## Exit Criteria
All 2D views render via Metal. W/L, zoom, pan, rotate, annotations all working. Zero OpenGL in DCMView.

## Estimated Effort
4–6 weeks (largest volume of work)

## Dependencies
- Sprint 3 (VTK migration)
ISSUE_EOF
)" && echo "  ✓ Sprint 4" || echo "  ✗ Sprint 4 failed"

# Sprint 5
gh issue create --repo "$REPO" \
  --title "Sprint 5: ROI Rendering & CPR Views Metal Migration" \
  --milestone "Phase 2: Rendering Migration (Sprints 3-6)" \
  --label "sprint:5,type:migration,area:rendering,priority:high" \
  --body "$(cat <<'ISSUE_EOF'
## Objective
Migrate ROI drawing (201+ GL refs) and all CPR/specialized 2D views to Metal.

## Tasks

### 5.1 ROI primitive rendering
- [ ] `ROI.m` (201+ GL refs) → Metal vertex buffers
- [ ] All ROI types: rect, ellipse, polygon, freehand, pencil, angle, arrow, text, measurement, 2D point

### 5.2 ROI interaction
- [ ] Hit testing → geometric calculation (replace OpenGL picking)
- [ ] Drag handles, resize, move

### 5.3 CPR views
- [ ] `CPRMPRDCMView.m` (81 GL refs)
- [ ] `CPRStraightenedView.m` (66 GL refs)
- [ ] `CPRStretchedView.m` (48 GL refs)
- [ ] `CPRTransverseView.m`

### 5.4 Remaining 2D OpenGL views
- [ ] `OrthogonalMPRView.m`
- [ ] `MPRDCMView.m` (31 GL refs)
- [ ] `EndoscopyMPRView.m`
- [ ] `LLScoutView.m`
- [ ] `CalciumScoringWindowController.m`

## Exit Criteria
All ROI types render on Metal. All CPR/specialized views migrated. Zero OpenGL in Horos/Sources.

## Estimated Effort
2–3 weeks

## Dependencies
- Sprint 4 (2D Metal infrastructure)
ISSUE_EOF
)" && echo "  ✓ Sprint 5" || echo "  ✗ Sprint 5 failed"

# Sprint 6
gh issue create --repo "$REPO" \
  --title "Sprint 6: Remove OpenGL Completely" \
  --milestone "Phase 2: Rendering Migration (Sprints 3-6)" \
  --label "sprint:6,type:cleanup,area:rendering,priority:high" \
  --body "$(cat <<'ISSUE_EOF'
## Objective
Eliminate all OpenGL framework references and verify Metal rendering end-to-end.

## Tasks

### 6.1 Remove OpenGL framework dependency
- [ ] Remove `OpenGL.framework` from Xcode project
- [ ] Remove all `#import <OpenGL/*>` includes
- [ ] Remove `CGLMacro.h` usage (14 files)
- [ ] Clean remaining GL utility code

### 6.2 End-to-end verification
- [ ] 2D viewer: single image, series scroll, 4D cine, multi-frame
- [ ] Window/level: all presets, custom W/L
- [ ] All ROI types: create, edit, delete, copy/paste, import/export
- [ ] MPR: orthogonal, oblique, CPR
- [ ] Volume rendering: ray cast, MIP, shaded surface
- [ ] Surface rendering
- [ ] Measurements, annotations, key images
- [ ] Export: screenshot, movie, DICOM secondary capture

### 6.3 Performance validation
- [ ] Rendering performance comparison
- [ ] GPU utilization profiling on Apple Silicon
- [ ] Frame drop check during scrolling and 3D rotation
- [ ] Memory usage verification

## Exit Criteria
OpenGL.framework removed. All rendering via Metal. Performance meets or exceeds baseline.

## Estimated Effort
1 week

## Dependencies
- Sprint 5 (ROI Metal)
ISSUE_EOF
)" && echo "  ✓ Sprint 6" || echo "  ✗ Sprint 6 failed"

# Sprint 7
gh issue create --repo "$REPO" \
  --title "Sprint 7: Deprecated API Cleanup" \
  --milestone "Phase 3: Cleanup & Sustainability (Sprints 7-9)" \
  --label "sprint:7,type:cleanup,priority:medium" \
  --body "$(cat <<'ISSUE_EOF'
## Objective
Systematic removal of all deprecated macOS APIs. **Can run parallel with Phase 2.**

## Tasks

### 7.1 Carbon framework removal (6 files)
- [ ] CSMailMailClient.m, Mailer.h, OSIWindowController.m, OnOffSwitchControlCell.m, Photos.h, Reports.h
- [ ] Replace Gestalt() → NSProcessInfo.operatingSystemVersion
- [ ] Replace FSRef/FSPathMakeRef → NSURL

### 7.2 QTKit → AVFoundation (12 files)
- [ ] Verify AVFoundation migration complete
- [ ] Rename QTKit-era method names

### 7.3 NSCalendarDate → modern date APIs (42 files)
- [ ] Replace with NSDateComponents/NSCalendar/NSDateFormatter
- [ ] Special attention to DICOM date parsing

### 7.4 WebView → WKWebView (9 files)
- [ ] PluginManagerController, SplashScreen, StructuredReportController, Decompress

### 7.5 NSURLConnection → NSURLSession (2 files)
- [ ] BrowserController.m, WADODownload.m

### 7.6 Other deprecated APIs
- [ ] stringWithCString: → stringWithCString:encoding: (65 occurrences)
- [ ] propertyListFromData: → modern API (8 files)
- [ ] AddressBook → Contacts framework
- [ ] Replace vendored SBJSON with NSJSONSerialization
- [ ] NSMatrix → NSCollectionView/NSStackView (46 files, prioritize visible UI)

## Exit Criteria
Zero deprecated API warnings with `-Wdeprecated-declarations`. All pragma suppressions removed.

## Estimated Effort
2–3 weeks

## Dependencies
- Sprint 0 (build system) — can start as soon as Sprint 0 is done
ISSUE_EOF
)" && echo "  ✓ Sprint 7" || echo "  ✗ Sprint 7 failed"

# Sprint 8
gh issue create --repo "$REPO" \
  --title "Sprint 8: Plugin SDK Modernization" \
  --milestone "Phase 3: Cleanup & Sustainability (Sprints 7-9)" \
  --label "sprint:8,type:plugin,priority:high" \
  --body "$(cat <<'ISSUE_EOF'
## Objective
Update the plugin architecture for Metal rendering. **DECIDED: Hard break — no backward compatibility shim.**

## Tasks

### 8.1 Plugin SDK versioning
- [ ] Define HOROS_PLUGIN_SDK_VERSION 5.0
- [ ] Update API/HorosAPI.m
- [ ] Add SDK version check in PluginManager.loadPluginBundle:

### 8.2 Plugin rendering API
- [ ] New protocol: \`drawInMetalView:encoder:\`
- [ ] Update PluginFilter.h protocol with Metal methods
- [ ] Remove OpenGL rendering methods from plugin API

### 8.3 Plugin signature validation
- [ ] Implement actual code signature validation (SecStaticCode)
- [ ] Require Developer ID signing in hardened runtime mode

### 8.4 gerinsights/horosplugins rewrite
- [ ] Audit each plugin for OpenGL, deprecated APIs, arch compatibility
- [ ] Rewrite plugins with Metal rendering
- [ ] Contribute upstream patches to horosproject/horosplugins where applicable
- [ ] Create per-plugin migration issues

### 8.5 Plugin loading security
- [ ] Verify plugin loading with hardened runtime + entitlements
- [ ] Test unsigned plugins in development mode

## Exit Criteria
Plugin SDK 5.0 with Metal rendering. Signature validation working. horosplugins audit complete.

## Estimated Effort
2 weeks

## Dependencies
- Sprint 6 (OpenGL fully removed)
ISSUE_EOF
)" && echo "  ✓ Sprint 8" || echo "  ✗ Sprint 8 failed"

# Sprint 9
gh issue create --repo "$REPO" \
  --title "Sprint 9: Stabilization, Testing & Release" \
  --milestone "Phase 3: Cleanup & Sustainability (Sprints 7-9)" \
  --label "sprint:9,type:testing,priority:high" \
  --body "$(cat <<'ISSUE_EOF'
## Objective
Production-quality release of the modernized fork.

## Tasks

### 9.1 Comprehensive testing
- [ ] DICOM conformance: CT, MR, US, XA, CR, DX, PT, NM, MG, SC, SR, PR, KO, SEG
- [ ] Transfer syntaxes: Implicit VR LE, Explicit VR LE/BE, JPEG, JPEG2000, JPEG-LS, RLE
- [ ] Multi-frame, enhanced, color, 4D datasets
- [ ] PACS: C-STORE, C-FIND, C-MOVE, C-GET, TLS
- [ ] Performance benchmarks (100/1K/5K images, 3D volumes)
- [ ] Memory and GPU profiling on Apple Silicon

### 9.2 CI/CD hardening
- [ ] Automated unit tests for critical paths
- [ ] DICOM test dataset in CI
- [ ] Notarization pipeline

### 9.3 Documentation
- [ ] FORK_DIFFERENCES.md
- [ ] PLUGIN_MIGRATION_GUIDE.md
- [ ] BUILD.md for Apple Silicon
- [ ] Update embedded help and about screen

### 9.4 Distribution
- [ ] Notarize with Apple
- [ ] Create DMG/installer
- [ ] GitHub Releases tag (v5.0.0)

## Exit Criteria
All tests passing. Application notarized. Distribution package built. Documentation complete.

## Estimated Effort
2–3 weeks

## Dependencies
- All prior sprints
ISSUE_EOF
)" && echo "  ✓ Sprint 9" || echo "  ✗ Sprint 9 failed"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Review created issues at: https://github.com/$REPO/issues"
echo "  2. Review milestones at: https://github.com/$REPO/milestones"
echo "  3. Optionally create a GitHub Project board and link issues"
echo "  4. Begin Sprint 0"
