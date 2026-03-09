# Plugin Requirements Specification

Version: 5.0 (target for gerinsights/horos modernization)

This document defines the requirements for Horos plugins under the modernized SDK. Use this spec to audit `gerinsights/horosplugins` content.

---

## 1. Build Requirements

| Requirement | Value | Notes |
|-------------|-------|-------|
| Architecture | `arm64` | Apple Silicon native required |
| Deployment target | macOS 14.0+ | Match main app |
| C++ standard | C++17 (if using C++) | Match main app |
| SDK | HorosAPI.framework 5.0 | Hard break from older SDK |
| Bundle extension | `.horosplugin` | `.osirixplugin` still loaded for compat |
| Package type | `BNDL` | Standard macOS bundle |
| Code signing | Developer ID recommended | Hardened runtime validated |

## 2. SDK Protocol Requirements

### Required: PluginFilter subclass

```objc
@interface MyPlugin : PluginFilter
// Must implement at least one entry point
- (long)filterImage:(NSString *)menuName;      // Image filter plugins
- (long)processFiles:(NSMutableArray *)files;   // Pre-process plugins
- (id)report:(NSManagedObject *)study action:(NSString *)action;  // Report plugins
@end
```

### Required Info.plist keys

| Key | Type | Description |
|-----|------|-------------|
| `NSPrincipalClass` | String | Main plugin class name |
| `pluginType` | String | One of: `imageFilter`, `roiTool`, `Database`, `fusionFilter`, `other` |
| `CFBundlePackageType` | String | Must be `BNDL` |
| `HorosPluginSDKVersion` | String | **NEW** — must be `5.0` |

### Optional Info.plist keys

| Key | Type | Description |
|-----|------|-------------|
| `MenuTitles` | Array | Menu item titles for the plugin |
| `ToolbarIcon` | String | Toolbar icon image name |
| `allowToolbarIcon` | Boolean | Whether plugin appears in toolbar |

## 3. Rendering Requirements (SDK 5.0)

### Prohibited APIs (will not compile/link)

- `NSOpenGLView`, `NSOpenGLContext`, `NSOpenGLPixelFormat`
- `OpenGL.framework` — removed from link dependencies
- `glBegin`, `glEnd`, `glVertex*`, `glColor*`, etc.
- `CGLMacro.h`

### Metal Rendering Protocol (NEW)

Plugins that need custom rendering must implement:

```objc
@protocol HorosPluginRendering <NSObject>
@optional
/// Draw plugin content using Metal render encoder
- (void)drawInMetalView:(MTKView *)view
         renderEncoder:(id<MTLRenderCommandEncoder>)encoder;
@end
```

Plugins that only process pixel data (no custom drawing) are unaffected.

### Text Rendering

- Use Core Text + MTLTexture (replacing StringTexture/GLString)
- SDK will provide helper methods for text overlay rendering

## 4. Prohibited Deprecated APIs

Plugins must not use any of the following:

| Deprecated API | Replacement |
|----------------|-------------|
| Carbon.framework | Cocoa equivalents |
| QuickTime.framework | AVFoundation |
| QTKit.framework | AVFoundation |
| NSCalendarDate | NSDateComponents + NSCalendar |
| WebView | WKWebView |
| NSURLConnection | NSURLSession |
| AddressBook.framework | Contacts.framework |
| `stringWithCString:` (no encoding) | `stringWithCString:encoding:` |
| NSMatrix | NSCollectionView / NSStackView |
| OSSpinLock | os_unfair_lock |
| `propertyListFromData:` | `propertyListWithData:options:format:error:` |
| Gestalt() | NSProcessInfo.operatingSystemVersion |
| FSRef / FSPathMakeRef | NSURL |
| Method swizzling on Horos classes | SDK extension points |

## 5. Plugin Audit Checklist

Use this checklist when auditing each plugin in `gerinsights/horosplugins`:

```
Plugin: _______________
Date audited: _______________

BUILD
[ ] Has .xcodeproj
[ ] Compiles for arm64
[ ] Deployment target >= 14.0
[ ] Links against HorosAPI.framework 5.0
[ ] Info.plist has HorosPluginSDKVersion = 5.0

RENDERING
[ ] No OpenGL imports (#import <OpenGL/*>)
[ ] No NSOpenGLView usage
[ ] No direct GL calls (glBegin, glVertex, etc.)
[ ] Custom rendering uses Metal protocol (if applicable)
[ ] No CGLMacro.h usage

DEPRECATED APIS
[ ] No Carbon.framework
[ ] No QuickTime/QTKit
[ ] No NSCalendarDate
[ ] No WebView (use WKWebView)
[ ] No NSURLConnection (use NSURLSession)
[ ] No NSMatrix
[ ] No OSSpinLock
[ ] No method swizzling on Horos classes

DEPENDENCIES
[ ] No embedded frameworks with wrong architecture
[ ] ITK/VTK references updated to current versions (if applicable)
[ ] All linked frameworks available on macOS 14+

FUNCTIONALITY
[ ] Plugin loads without crash
[ ] Core functionality works
[ ] UI renders correctly
[ ] No deprecation warnings at compile time
```

## 6. Plugin Inventory — Audit Status

| Plugin | Type | Complexity | OpenGL | Deprecated APIs | Audit Status |
|--------|------|-----------|--------|-----------------|-------------|
| CalciumScore | imageFilter | Simple | No | Unknown | Not started |
| CloseThisStudy | other | Minimal | No | None expected | Not started |
| CMIV_CTA_TOOLS | imageFilter | Heavy (VTK) | Yes | Likely | Not started |
| Cobb Angle | roiTool | Simple | No | None expected | Not started |
| Duplicate | other | Minimal | No | None expected | Not started |
| ExtraDatabaseColumnsSample | Database | Moderate | No | Method swizzling | Not started |
| HelloWorld | imageFilter | Minimal | No | None expected | Not started |
| HipArthroplastyTemplating | roiTool | Moderate | No | NSBitmapImageRep | Not started |
| JPEG to DICOM | imageFilter | Simple | No | Unknown | Not started |
| MIRC Teaching File | other | Heavy | No | WebView, SeqGrab | Not started |
| NMSegmentation | imageFilter | Heavy (ITK) | No | Unknown | Not started |
| OpenGL | other | Moderate | **Yes** | NSOpenGLView | Not started |
| PDF to DICOM | imageFilter | Simple | No | Unknown | Not started |
| PetSpectFusion | fusionFilter | Heavy (ITK+VTK) | Yes | Unknown | Not started |
| Sample Menu | other | Minimal | No | None expected | Not started |
| VoxelVolume | imageFilter | Heavy (VTK) | Yes | Many | Not started |
| WindowAnchoredAnnotations | other | Simple | No | QuartzCore | Not started |

*Note: This table covers notable plugins. Full audit of all 84 plugins pending Sprint 8.*

## 7. Migration Priority

**Priority 1 — Simple plugins (validate build + arm64):**
HelloWorld, CloseThisStudy, Duplicate, Cobb Angle, Sample Menu, CalciumScore, JPEG to DICOM, PDF to DICOM

**Priority 2 — Moderate plugins (deprecated API fixes):**
HipArthroplastyTemplating, WindowAnchoredAnnotations, ExtraDatabaseColumnsSample

**Priority 3 — Heavy plugins (rendering + dependency migration):**
CMIV_CTA_TOOLS, PetSpectFusion, NMSegmentation, VoxelVolume, OpenGL demo

**Priority 4 — Complex UI plugins (WebView, SeqGrab replacement):**
MIRC Teaching File, DiscPublishing

**Defer / Remove:**
Plugins in `_obsolete/` (64bit, AutoClean, Casimage)
