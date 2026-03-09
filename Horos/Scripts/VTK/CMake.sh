#!/bin/sh

export PATH="$PATH:/opt/local/bin:/opt/local/sbin:/opt/homebrew/bin/"

path="$( cd "$(dirname "${BASH_SOURCE[0]}")" && pwd )/$(basename "${BASH_SOURCE[0]}")"
cd "$TARGET_NAME"; pwd

env=$(env|sort|grep -v 'LLBUILD_BUILD_ID=\|LLBUILD_LANE_ID=\|LLBUILD_TASK_ID=\|Apple_PubSub_Socket_Render=\|DISPLAY=\|SHLVL=\|SSH_AUTH_SOCK=\|SECURITYSESSIONID=')
hash="$(git describe --always --tags --dirty) $(md5 -q "$path")-$(md5 -qs "$env")"

set -e; set -o xtrace

cmake_dir="$TARGET_TEMP_DIR/CMake"
install_dir="$TARGET_TEMP_DIR/Install"

mkdir -p "$cmake_dir"; cd "$cmake_dir"
if [ -e Makefile -a -f .cmakehash ] && [ "$(cat '.cmakehash')" = "$hash" ]; then
    exit 0
fi

if [ -e ".cmakeenv" ]; then
echo "Rebuilding.."
cat '.cmakeenv'
echo "$env"
fi


command -v cmake >/dev/null 2>&1 || { echo >&2 "error: building $TARGET_NAME requires CMake. Please install CMake. Aborting."; exit 1; }
command -v pkg-config >/dev/null 2>&1 || { echo >&2 "error: building $TARGET_NAME requires pkg-config. Please install pkg-config. Aborting."; exit 1; }
command -v git-lfs >/dev/null 2>&1 || { echo >&2 "error: building $TARGET_NAME requires git-lfs. Please install git-lfs. Aborting."; exit 1; }

[ -d "$cmake_dir" ] && mv "$cmake_dir" "$cmake_dir.tmp"
[ -d "$install_dir" ] && mv "$install_dir" "$install_dir.tmp"
rm -Rf "$cmake_dir.tmp" "$install_dir.tmp"
mkdir -p "$cmake_dir"; cd "$cmake_dir"

args=("$PROJECT_DIR/$TARGET_NAME") # -G Xcode
cxxfs=( -w -fvisibility=default )
args+=(-DVTK_USE_X:BOOL=OFF)
args+=(-DVTK_USE_COCOA:BOOL=ON)
#args+=(-DVTK_USE_64BITS_IDS=ON) 
args+=(-DBUILD_DOCUMENTATION=OFF)
args+=(-DBUILD_EXAMPLES=OFF)
args+=(-DBUILD_SHARED_LIBS=OFF)
args+=(-DBUILD_TESTING=OFF)
args+=(-DCMAKE_POLICY_VERSION_MINIMUM=3.5)
args+=(-DCMAKE_OSX_DEPLOYMENT_TARGET="$MACOSX_DEPLOYMENT_TARGET")
args+=(-DCMAKE_OSX_ARCHITECTURES="$ARCHS")

# VTK 9: system third-party library flags (renamed from VTK_USE_SYSTEM_*)
args+=(-DVTK_MODULE_USE_EXTERNAL_VTK_zlib=ON)
args+=(-DVTK_MODULE_USE_EXTERNAL_VTK_expat=ON)
args+=(-DVTK_MODULE_USE_EXTERNAL_VTK_libxml2=ON)

# args+=(-DCMAKE_VERBOSE_MAKEFILE:BOOL=ON)

[ "$CONFIGURATION" == 'Release' ] && args+=( -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE=-O3 )

# VTK 9: suppress groups by default but allow transitive deps to pull them in.
# Use DONT_WANT (not NO) so dependency resolution can enable required sub-modules.
args+=(-DVTK_GROUP_ENABLE_StandAlone=DONT_WANT)
args+=(-DVTK_GROUP_ENABLE_Rendering=DONT_WANT)
args+=(-DVTK_MODULE_ENABLE_VTK_RenderingOpenGL2=YES)
args+=(-DVTK_MODULE_ENABLE_VTK_RenderingVolumeOpenGL2=YES)
args+=(-DVTK_MODULE_ENABLE_VTK_RenderingAnnotation=YES)
args+=(-DVTK_MODULE_ENABLE_VTK_InteractionWidgets=YES)
args+=(-DVTK_MODULE_ENABLE_VTK_IOImage=YES)
args+=(-DVTK_MODULE_ENABLE_VTK_IOGeometry=YES)
args+=(-DVTK_MODULE_ENABLE_VTK_IOExport=YES)
args+=(-DVTK_MODULE_ENABLE_VTK_FiltersGeneral=YES)
args+=(-DVTK_MODULE_ENABLE_VTK_ImagingMorphological=YES)
args+=(-DVTK_MODULE_ENABLE_VTK_ImagingStencil=YES)
args+=(-DVTK_MODULE_ENABLE_VTK_FiltersTexture=YES)
# FiltersPoints provides vtkPowerCrustSurfaceReconstruction (used in ROIVolumeView.mm)
args+=(-DVTK_MODULE_ENABLE_VTK_FiltersPoints=YES)
# Metal backend preference (no separate RenderingMetal module in VTK 9.6)
args+=(-DVTK_USE_METAL=ON)
# Fail at compile time on any legacy VTK API usage
args+=(-DVTK_LEGACY_REMOVE=ON)

args+=(-DCMAKE_INSTALL_PREFIX="$install_dir")
args+=(-DVTK_INSTALL_INCLUDE_DIR="include")

args+=(-DCMAKE_IGNORE_PATH="/opt/local/include;/opt/local/lib")

if [ ! -z "$CLANG_CXX_LIBRARY" ] && [ "$CLANG_CXX_LIBRARY" != 'compiler-default' ]; then
#    args+=(-DCMAKE_XCODE_ATTRIBUTE_CLANG_CXX_LIBRARY="$CLANG_CXX_LIBRARY")
    cxxfs+=(-stdlib="$CLANG_CXX_LIBRARY")
fi
if [ ! -z "$CLANG_CXX_LANGUAGE_STANDARD" ]; then
#    args+=(-DCMAKE_XCODE_ATTRIBUTE_CLANG_CXX_LANGUAGE_STANDARD="$CLANG_CXX_LANGUAGE_STANDARD")
    cxxstd="$CLANG_CXX_LANGUAGE_STANDARD"
    cxxfs+=(-std="$cxxstd")
fi

# Remove any lingering -std=c++0x from toolchain defaults
for i in "${!cxxfs[@]}"; do
    if [ "${cxxfs[$i]}" = "-std=c++0x" ]; then
        unset 'cxxfs[$i]'
    fi
done
cxxfs+=( -std=c++17 )

if [ ${#cxxfs[@]} -ne 0 ]; then
    cxxfss="${cxxfs[@]}"
    args+=(-DCMAKE_CXX_FLAGS="$cxxfss")
fi

# Force a modern C++ standard for VTK/eigen compatibility
args+=(-DCMAKE_CXX_STANDARD=17)
args+=(-DCMAKE_CXX_STANDARD_REQUIRED=ON)

cmake "${args[@]}"

echo "$hash" > "$cmake_dir/.cmakehash"
echo "$env" > "$cmake_dir/.cmakeenv"

exit 0
