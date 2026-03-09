# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Horos is a macOS DICOM medical imaging workstation (Objective-C/C++, ~340 source files, zero Swift). This is the `gerinsights/horos` fork — a forward-only modernization of horosproject/horos v4.0.0 RC5 (last released August 2022). Not backport-compatible with upstream.

**License:** GNU LGPL v3

## Build Commands

```bash
# Prerequisites: cmake, pkg-config, git-lfs
# Install via: brew install cmake pkg-config git-lfs

# GUI build
open Horos.xcodeproj  # Build with Cmd+B, scheme "Horos"

# Terminal build (Debug)
make

# Terminal build (Release)
make CONFIG=Release

# Underlying xcodebuild command
xcodebuild -project Horos.xcodeproj -scheme Horos -configuration Debug -derivedDataPath build

# Initialize submodules (build does this automatically)
git submodule update --init --recursive

# Unzip pre-compiled binaries (build does this automatically)
# Build target: "Unzip Binaries"
```

First build takes 5-30 minutes (compiling VTK, ITK, etc. from source).

## Build Schemes

- **Horos** — main application
- **Horos API** — plugin SDK framework (HorosAPI.framework)
- **Horos DCM** — DICOM parsing framework
- **DICOMPrint** — DICOM print helper
- **Decompress** — decompression helper
- **Unzip Binaries** / **Cleanup Binaries** — pre-compiled binary management

## Build Configuration

- `Config.xcconfig` — global settings (ARCHS, deployment target, team ID)
- `Horos/Horos.xcconfig` — version and bundle ID
- Currently: arm64, macOS 11.0, C++11 (modernization targets: macOS 14, C++17)

## Architecture

### Critical Data Path
```
CoreData (DicomStudy/Series/Image)
  -> DICOM Parsing (DCM Framework + DCMTK)
    -> Pixel Buffer (DCMPix)
      -> 2D Rendering (DCMView — OpenGL, migrating to Metal)
      -> 3D Rendering (VRView/SRView — VTK + OpenGL)
  -> DICOM Network (DCMTK C-STORE/C-FIND/C-MOVE)
```

### Key Source Files (Horos/Sources/)

**Massive files — modify surgically, don't refactor:**
- `ViewerController.m` (22,872 lines) — 2D viewer window controller
- `BrowserController.m` (20,737 lines) — database browser/study management
- `DCMView.m` (14,526 lines) — 2D OpenGL rendering, tools, interactions
- `AppController.m` (5,813 lines) — NSApplication delegate

**Rendering pipeline:**
- `DCMView.m` — 2D DICOM display (356 GL references, primary Metal migration target)
- `ROI.m` — region of interest drawing (201 GL references)
- `VRView.mm` / `SRView.mm` — 3D volume/surface rendering via VTK
- `CPR*.m` — curved planar reformation views
- `MPR*.m` — multi-planar reformation views
- `StringTexture.m`, `GLString.m` — text rendering via OpenGL textures
- `NavigatorView.m`, `LoupeView.m`, `PreviewView.m` — auxiliary GL views

**Data model:**
- `Horos/Models/OsiriXDB_DataModel.xcdatamodeld` — Core Data DICOM database
- `DicomImage.h/m`, `DicomSeries.h/m`, `DicomStudy.h/m` — entity classes
- `DCMPix.h/m` — single DICOM image pixel data

**Plugin system:**
- `PluginFilter.h` — base class all plugins subclass
- `PluginManager.h/m` — plugin loading, discovery, lifecycle
- `OSIEnvironment.h/m` — plugin SDK entry point (singleton)
- `API/HorosAPI.m` — plugin framework wrapper

### Companion Frameworks

- `DCM Framework/` — DICOM parsing (59 subdirectories, handles all transfer syntaxes)
- `Nitrogen/` — Objective-C++ image processing framework (183 source files, has own unit tests)
- `DicomImporter/` — Spotlight metadata importer for DICOM files

### Submodules (9 total, all outdated)

| Library | Role | Build Script |
|---------|------|-------------|
| VTK | 3D visualization | `Horos/Scripts/VTK/CMake.sh` |
| ITK | Image analysis | `Horos/Scripts/ITK/CMake.sh` |
| DCMTK | DICOM toolkit | `Horos/Scripts/DCMTK/CMake.sh` |
| OpenSSL | TLS/crypto | `Horos/Scripts/OpenSSL/Config.sh` |
| GDCM | DICOM codec | `Horos/Scripts/GDCM/CMake.sh` |
| OpenJPEG | JPEG 2000 | `Horos/Scripts/OpenJPEG/CMake.sh` |
| CharLS | JPEG-LS | `Horos/Scripts/CharLS/CMake.sh` |
| Grok | JPEG 2000 (removing) | `Horos/Scripts/Grok/CMake.sh` |
| FeedbackReporter | Crash reporting | — |

## Modernization Plan

Active sprint plan tracked via GitHub milestones and issues on `gerinsights/horos`:
- **Phase 1** (Sprints 0-2): Build system, security deps, dependency updates
- **Phase 2** (Sprints 3-6): VTK 8->9, OpenGL->Metal migration
- **Phase 3** (Sprints 7-9): Deprecated API cleanup, plugin SDK, release

Key decisions (see `MODERNIZATION_SPRINT_PLAN.md` on PR branch):
- Grok: **Remove** (consolidate on OpenJPEG)
- VTK target: **9.6.0**
- Plugin backward compat: **Hard break** (plugins must adopt Metal)
- Fork stance: **Forward-only** (not backport-capable)

## Plugin System

Plugins are NSBundle (.horosplugin/.osirixplugin) loaded at runtime.

**Plugin types:** `imageFilter`, `roiTool`, `Database`, `fusionFilter`, `reportPlugin`, `preProcessPlugin`

**Plugin entry points:**
- `filterImage:` — image processing
- `processFiles:` — pre-processing
- `report:action:` — report generation
- `handleEvent:forViewer:` — event interception
- `toolbarAllowedIdentifiersForViewer:` — toolbar customization

**Plugin SDK framework names** (all built from same source, for compatibility):
- HorosAPI.framework, OsiriXAPI.framework, OsiriX Headers.framework, HorosDCM.framework

**Sister repo:** `gerinsights/horosplugins` — 84 plugins, all need arm64 + Metal migration.

## Testing

Minimal test infrastructure:
- `Horos/Unit Tests/` — DICOMFilesTests, basic test base
- `Nitrogen/Unit Tests/` — Nitrogen framework tests
- No CI test suite yet (GitHub Actions CI for build only)

## Conventions

- Objective-C throughout (no Swift). ObjC++ (.mm) only where C++ interop needed (VTK, ITK, DCMTK).
- Headers use `#import`, not `#include`
- Many classes carry OsiriX-era naming (OSI* prefix = OsiriX plugin SDK classes)
- URL schemes: `horos://`, `osirix://`
- Localization: English (en.lproj) and Japanese (ja-JP.lproj)
- DICOM standards compliance is paramount — never break DICOM import/export/network
