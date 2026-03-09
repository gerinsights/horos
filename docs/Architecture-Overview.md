# Architecture Overview

## Application Stack

```
┌─────────────────────────────────────────────┐
│                  Horos.app                   │
├─────────────────────────────────────────────┤
│  AppController (lifecycle, preferences)     │
│  BrowserController (DICOM database, study   │
│    management, 20K+ lines)                  │
│  ViewerController (2D viewer windows,       │
│    22K+ lines)                              │
├─────────────────────────────────────────────┤
│  Rendering Pipeline                         │
│  ┌──────────────┐  ┌─────────────────────┐  │
│  │ 2D: DCMView  │  │ 3D: VRView/SRView  │  │
│  │ (OpenGL→     │  │ (VTK 8→9 + OpenGL  │  │
│  │  Metal)      │  │  →Metal)           │  │
│  │ ROI drawing  │  │ Volume rendering   │  │
│  │ CPR/MPR      │  │ Surface rendering  │  │
│  └──────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────┤
│  Data Layer                                 │
│  DCMPix (pixel buffers)                     │
│  CoreData (DicomStudy/Series/Image)         │
│  DCM Framework (DICOM parsing)              │
├─────────────────────────────────────────────┤
│  DICOM Network (DCMTK)                      │
│  C-STORE, C-FIND, C-MOVE, C-GET, TLS       │
├─────────────────────────────────────────────┤
│  Plugin System (NSBundle dynamic loading)   │
│  PluginFilter base class → 84 plugins       │
└─────────────────────────────────────────────┘
```

## Submodule Dependencies

```
Horos
├── VTK (8.2.0 → 9.6.0)    — 3D rendering, Metal backend in 9.4+
├── ITK (5.2.1 → 5.4.5)    — medical image analysis
├── DCMTK (3.6.7 → 3.7.0)  — DICOM network and parsing
├── OpenSSL (3.0.4 → 3.6.x) — TLS for DICOM connections
├── GDCM (3.0 → 3.2.2)     — DICOM image codec library
├── OpenJPEG (2.5.0 → 2.5.4) — JPEG 2000
├── CharLS (2.0.0 → 2.4.3)  — JPEG-LS
├── Grok (REMOVING)          — redundant JPEG 2000
└── FeedbackReporter          — crash reporting (evaluate removal)
```

## Companion Frameworks

- **DCM Framework** — full DICOM parser, handles all transfer syntaxes (Implicit VR LE, Explicit VR LE/BE, JPEG, JPEG2000, JPEG-LS, RLE)
- **Nitrogen** — Objective-C++ image processing framework with its own unit tests
- **DicomImporter** — macOS Spotlight metadata importer for DICOM files

## File Organization

```
horos/
├── Horos.xcodeproj/           # Main Xcode project
├── Config.xcconfig            # Global build settings (arch, deployment target)
├── Horos/
│   ├── Horos.xcconfig         # Version, bundle ID
│   ├── Sources/               # 352 headers, 339 implementations
│   ├── Scripts/               # Submodule build scripts (CMake wrappers)
│   ├── Models/                # Core Data models
│   ├── Resources/             # XIBs, presets, CLUTs, templates
│   ├── Unit Tests/            # Minimal test suite
│   └── Info.plist             # App bundle configuration
├── DCM Framework/             # DICOM parsing framework
├── Nitrogen/                  # Image processing framework
├── DICOMPrint/                # Print helper
├── Binaries/                  # Pre-compiled binaries, embedded plugins
├── API/                       # Plugin SDK framework source
└── [submodule dirs]/          # VTK, ITK, DCMTK, etc.
```

## Plugin Loading Architecture

1. Horos scans plugin directories at startup
2. Each `.horosplugin` / `.osirixplugin` is an NSBundle
3. `NSPrincipalClass` from Info.plist identifies the plugin class
4. Plugin must subclass `PluginFilter`
5. Horos calls `initPlugin` on load, `filterImage:` on activation
6. Plugins access the app via `ViewerController`, `BrowserController`, `DCMPix`, `ROI` APIs
7. Event handling via optional `handleEvent:forViewer:` protocol method

## Rendering Architecture (Current → Target)

### Current (OpenGL)
- `DCMView` subclasses `NSOpenGLView`
- Direct `glBegin`/`glEnd` calls for primitives
- `StringTexture`/`GLString` for text overlay rendering
- ROI drawn via GL immediate mode
- VTK uses its own OpenGL context for 3D

### Target (Metal)
- `HorosMTKView` (MTKView subclass) replaces NSOpenGLView
- `HorosMetalRenderer` — shared device, command queue, pipeline states
- Metal shaders for W/L, CLUT, primitives
- ROI via Metal vertex buffers
- VTK 9.6 native Metal backend for 3D
