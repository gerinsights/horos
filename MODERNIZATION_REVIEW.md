# Horos Modernization Review

**Date:** 2026-03-08
**Current Version:** Horos v4.0.0 RC5 (Build 20220801)
**Last Release:** August 1, 2022

This document identifies updates needed to bring Horos in line with current-generation macOS and toolchain requirements.

---

## 1. Deployment Target & SDK

| Setting | Current | Recommended |
|---------|---------|-------------|
| `MACOSX_DEPLOYMENT_TARGET` | 11.0 (Big Sur) | **13.0 (Ventura)** or **14.0 (Sonoma)** |
| `ARCHS` | arm64 only | arm64 (keep; or add x86_64 Universal) |
| `CLANG_CXX_LANGUAGE_STANDARD` | c++0x (C++11) | **c++17** |
| `GCC_C_LANGUAGE_STANDARD` | c11 | c11 (no change needed) |
| Xcode compatibility | Xcode 14+ | **Xcode 16+** |

**Notes:**
- macOS 11 Big Sur reached end of life in September 2023. macOS 12 Monterey reached EOL in September 2024. Targeting macOS 13+ aligns with Apple's current support window.
- Xcode 16 sets a floor of macOS 11.5 for deployment targets by default; this is not a blocker but signals Apple's direction.
- C++11 (`c++0x`) is outdated. Several dependencies (CharLS, ITK 6, DCMTK 3.7) now require or recommend C++17. Upgrading to C++17 is necessary for dependency updates.
- The `Config.xcconfig` file at the project root is the single source for these settings.

**Files to modify:**
- `Config.xcconfig` (lines 13, 16)
- `Horos.xcodeproj/project.pbxproj` (CLANG_CXX_LANGUAGE_STANDARD)

---

## 2. Third-Party Dependencies (Submodules)

All submodules are pinned to 2022-era commits and are significantly outdated.

| Library | Pinned Version (approx.) | Latest Stable | Priority | Notes |
|---------|-------------------------|---------------|----------|-------|
| **OpenSSL** | ~3.0.x (2022) | **3.6.1** (Jan 2026) | **CRITICAL** | Security library; 3.0 LTS EOL Sep 2026. Contains known CVE fixes. |
| **DCMTK** | ~3.6.7 (2022) | **3.7.0** (Dec 2025) | **HIGH** | Core DICOM toolkit; includes DICOM standard updates and bug fixes. |
| **VTK** | ~9.1.x (2022) | **9.6.0** (Feb 2026) | **HIGH** | Visualization toolkit; major Metal rendering improvements in 9.4+. |
| **ITK** | ~5.2.x (2022) | **5.4.5** / 6.0 beta | **HIGH** | Image analysis; ITK 6 requires C++17, deprecates Intel macOS. |
| **GDCM** | ~3.0.x (2022) | **3.2.2** | **MEDIUM** | DICOM library; includes security fixes (CISA advisory for OOB write). |
| **OpenJPEG** | ~2.5.0 (2022) | **2.5.4** (Sep 2025) | **MEDIUM** | JPEG 2000; bugfix releases with stability improvements. |
| **CharLS** | ~2.3.x (2022) | **2.4.x+** | **MEDIUM** | JPEG-LS codec; now requires C++17. |
| **Grok** | 2022 snapshot | Latest | **LOW** | JPEG 2000 compression. |
| **FeedbackReporter** | 2022 snapshot | Unmaintained | **LOW** | Consider replacing or removing. |

**Recommended approach:**
1. Update OpenSSL first (security-critical)
2. Update DCMTK and GDCM together (DICOM stack)
3. Update VTK and ITK together (imaging/visualization stack)
4. Update remaining libraries

---

## 3. Deprecated API Usage

### 3.1 OpenGL (CRITICAL)

**Status:** Deprecated since macOS 10.14 (2018). Still functional but frozen at OpenGL 4.1. Apple may remove it in a future macOS release.

**Scope:** ~1,065 OpenGL references across 70+ source files. This is the single largest modernization concern.

**Key affected files:**
- `DCMView.m` (356 GL references) — primary 2D DICOM viewer
- `ROI.m` (201 references) — Region of Interest drawing
- `NavigatorView.m` (70 references)
- `CPRMPRDCMView.m`, `CPRStretchedView.m` (55-59 references each)
- `LoupeView.m` (57 references)
- `OpenGLScreenReader.m` (40 references)
- `MPRDCMView.m` (31 references)
- 36 files use `NSOpenGLView`/`NSOpenGLContext`/`NSOpenGLPixelFormat`

**Recommendation:** This is a major undertaking. Options:
1. **Short-term:** Suppress deprecation warnings and continue using OpenGL (it still works on macOS 15)
2. **Medium-term:** Migrate rendering to Metal via `CAMetalLayer` or `MTKView`. VTK 9.4+ has native Metal support which could help with 3D views
3. **Long-term:** Full Metal migration for all custom rendering

### 3.2 QTKit (HIGH)

**Status:** Removed from macOS SDK. Code exists but appears partially migrated.

**Files using QTKit references (13 files):**
- `QuicktimeExport.h/m` — Already partially migrated (imports AVFoundation/CoreMedia, but method names still reference "QTKit": `createMovieQTKit:`)
- `VRView.mm`, `VRViewVPRO.mm`, `SRView.mm`, `SRView+StereoVision.mm`
- `MPRController.m`, `MPR2DController.mm`, `FlyThruController.mm`
- `CPRController.m`, `ViewerController.m`
- `Decompress.mm`

**Recommendation:** Audit all QTKit references. The header suggests AVFoundation is already imported, but method signatures and internal logic may still reference QTKit patterns. Complete the migration.

### 3.3 Carbon Framework (MEDIUM)

**Status:** Legacy C-based framework. Most APIs replaced by Cocoa equivalents.

**Files importing Carbon (6 files):**
- `Reports.h`, `Photos.h`, `Mailer.h`
- `OnOffSwitchControlCell.m`, `OSIWindowController.m`, `CSMailMailClient.m`

**Recommendation:** Replace Carbon imports with AppKit/Cocoa equivalents. Most uses are likely for key code constants or legacy event handling.

### 3.4 AddressBook Framework (MEDIUM)

**Status:** Deprecated in favor of Contacts framework since macOS 10.11.

**Files:**
- `StructuredReport.mm`, `IChatTheatreDelegate.m`
- Linked in `project.pbxproj`

**Recommendation:** Migrate to Contacts framework.

### 3.5 InstantMessage/iChat Framework (LOW)

**Status:** Removed. iChat was replaced by Messages in macOS 10.8.

**Files:**
- `IChatTheatreDelegate.h/m`, `IChatTheatreHelpWindowController.h/m`
- InstantMessage.framework linked in `project.pbxproj`

**Recommendation:** Remove iChat integration entirely. This functionality has been defunct for over a decade.

### 3.6 Legacy WebKit (WebView) (MEDIUM)

**Status:** Legacy `WebView` class deprecated in favor of `WKWebView`.

**Files (9 files):**
- `StructuredReportController.h/mm`
- `SplashScreen.h/m`
- `PluginManagerController.h/m`
- `IChatTheatreDelegate.h`
- `Decompress.mm`

**Recommendation:** Migrate from `WebView` to `WKWebView`.

### 3.7 NSURLConnection (MEDIUM)

**Status:** Deprecated in favor of `NSURLSession` since macOS 10.11.

**Files:**
- `N2WebServiceClient.mm`, `WADODownload.m`, `BrowserController.m`

**Recommendation:** Migrate to `NSURLSession` for all network operations.

### 3.8 OSSpinLock (HIGH)

**Status:** Deprecated and unsafe on modern systems (priority inversion bug). Replaced by `os_unfair_lock`.

**Files (7 files):**
- `N3BezierCore.m`, `WADODownload.m`, `DCMTKQueryNode.mm`
- `CPRVolumeData.m`, `CPRStretchedOperation.m`, `CPRStraightenedOperation.m`, `CPRObliqueSliceOperation.m`

**Recommendation:** Replace all `OSSpinLock` with `os_unfair_lock` or `NSLock`. This is a correctness issue, not just deprecation.

### 3.9 NSUserNotification (LOW)

**Status:** Deprecated in macOS 10.14, replaced by `UNUserNotificationCenter`.

**Note:** The project already links `UserNotifications.framework` — migration may be partially complete.

### 3.10 Embedded JSON Library (LOW)

**Status:** `Nitrogen/Sources/JSON/` contains a vendored SBJSON library (very old).

**Recommendation:** Replace with `NSJSONSerialization` (built into Foundation since macOS 10.7).

---

## 4. Build System & Toolchain

### 4.1 Vendored Binaries

- `Binaries/` directory contains pre-built DCMTK sources and Jasper library headers
- These are separate from the git submodule versions and may be inconsistent
- The Jasper JPEG 2000 library in `DCM Framework/jasper/` appears very old

**Recommendation:** Audit vendored binaries against submodule versions. Remove stale vendored copies where submodules provide the same functionality.

### 4.2 Legacy Sub-projects

- `Nitrogen/` — Utility library with legacy patterns (SBJSON, OpenGL helpers)
- `cocoahttpserver/` — References `MacOSX10.5.sdk`, supports `ppc` architecture
- `DicomImporter/` — Separate Xcode project, may need deployment target alignment

**Recommendation:** Update or remove legacy sub-project configurations.

### 4.3 Xcode Project Settings

- No hardened runtime entitlements configured (`Horos.entitlements` is empty)
- No App Sandbox configuration
- Missing code signing for distribution outside App Store

**Recommendation:** Configure hardened runtime (required for notarization on macOS 10.15+).

### 4.4 CI/CD

- No CI configuration files found (`.github/workflows/`, `.travis.yml`, etc.)

**Recommendation:** Add GitHub Actions workflow for automated builds and testing.

---

## 5. Code Quality Concerns

### 5.1 Massive Source Files

- `AppController.m` and `BrowserController.m` are extremely large monolithic files
- This makes maintenance, testing, and review difficult

### 5.2 `stringWithCString:` Usage

- 73 occurrences of deprecated `stringWithCString:` (no encoding parameter)
- Should use `stringWithCString:encoding:` or `stringWithUTF8String:`

### 5.3 `finalize` Method Implementations

- 18 files implement `-finalize` (garbage collection era method)
- GC was removed in macOS 10.12; these methods are dead code

---

## 6. Priority Roadmap

### Phase 1: Critical Security & Compatibility (Immediate)
- [ ] Update OpenSSL to 3.4+ LTS branch
- [ ] Replace `OSSpinLock` with `os_unfair_lock` (7 files)
- [ ] Update deployment target to macOS 13.0+
- [ ] Upgrade C++ standard to C++17
- [ ] Configure hardened runtime entitlements

### Phase 2: Dependency Updates (Near-term)
- [ ] Update DCMTK to 3.7.0
- [ ] Update GDCM to 3.2.x (security fix)
- [ ] Update VTK to 9.4+ (Metal rendering support)
- [ ] Update ITK to 5.4.x
- [ ] Update OpenJPEG and CharLS
- [ ] Remove iChat/InstantMessage integration

### Phase 3: API Modernization (Medium-term)
- [ ] Migrate `NSURLConnection` to `NSURLSession`
- [ ] Migrate `WebView` to `WKWebView`
- [ ] Replace Carbon imports with AppKit equivalents
- [ ] Replace AddressBook with Contacts framework
- [ ] Replace SBJSON with `NSJSONSerialization`
- [ ] Complete QTKit to AVFoundation migration
- [ ] Clean up `stringWithCString:` and `finalize` dead code
- [ ] Remove legacy `cocoahttpserver` ppc/i386 configuration

### Phase 4: OpenGL to Metal Migration (Long-term)
- [ ] Audit OpenGL usage patterns across 70+ files
- [ ] Leverage VTK 9.4+ Metal backend for 3D rendering
- [ ] Migrate custom 2D rendering (DCMView, ROI, NavigatorView) to Metal
- [ ] Replace `NSOpenGLView` subclasses with `MTKView`
- [ ] Remove OpenGL screen reader utility

### Phase 5: Project Infrastructure
- [ ] Add GitHub Actions CI/CD pipeline
- [ ] Add App Sandbox entitlements where feasible
- [ ] Break up monolithic controllers (AppController, BrowserController)
- [ ] Update `Horos.xcconfig` version to 5.0.0

---

## Summary

Horos has not seen a release since August 2022. The codebase has accumulated significant technical debt relative to the current macOS 15 Sequoia / Xcode 16 toolchain:

1. **9 submodule dependencies** are 3-4 years behind current releases, including security-critical OpenSSL
2. **OpenGL** (1,065 references, 70+ files) is the largest migration concern — deprecated since 2018 but still functional
3. **Multiple deprecated frameworks** are still in use (QTKit, Carbon, AddressBook, InstantMessage, legacy WebKit)
4. **Thread safety bug** via `OSSpinLock` usage (7 files) should be fixed immediately
5. **C++11 standard** prevents updating to latest versions of key dependencies
6. **No CI/CD** or hardened runtime configuration

The project is still buildable and functional on current macOS, but the window for addressing these issues narrows with each macOS release.
