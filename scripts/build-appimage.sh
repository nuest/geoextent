#!/bin/bash
# build-appimage.sh — Build a portable geoextent AppImage
#
# Uses conda-forge (via Miniforge) to install Python, GDAL, and all native
# dependencies into an AppDir, then packages everything with appimagetool.
#
# Usage:
#   bash scripts/build-appimage.sh
#
# Requirements:
#   - Linux x86_64
#   - ~2 GB disk space during build
#   - Internet access (first run downloads Miniforge + appimagetool)
#
# The resulting AppImage is written to the project root directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${PROJECT_DIR}/build/appimage"
APPDIR="${BUILD_DIR}/AppDir"
TOOLS_DIR="${BUILD_DIR}/tools"

ARCH="x86_64"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"

# ---------------------------------------------------------------------------
# Determine geoextent version from setuptools-scm (or fall back to git)
# ---------------------------------------------------------------------------
GEOEXTENT_VERSION="${GEOEXTENT_VERSION:-}"
if [ -z "${GEOEXTENT_VERSION}" ]; then
    GEOEXTENT_VERSION="$(cd "${PROJECT_DIR}" && python -c 'from setuptools_scm import get_version; print(get_version())' 2>/dev/null || true)"
fi
if [ -z "${GEOEXTENT_VERSION}" ]; then
    GEOEXTENT_VERSION="$(cd "${PROJECT_DIR}" && git describe --tags --always 2>/dev/null | sed 's/^v//' || echo "0.0.0")"
fi
echo "==> geoextent version: ${GEOEXTENT_VERSION}"

# ---------------------------------------------------------------------------
# 1. Download tools (cached between runs)
# ---------------------------------------------------------------------------
mkdir -p "${TOOLS_DIR}"

APPIMAGETOOL="${TOOLS_DIR}/appimagetool-${ARCH}.AppImage"
if [ ! -x "${APPIMAGETOOL}" ]; then
    echo "==> Downloading appimagetool..."
    curl -fSL "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage" \
        -o "${APPIMAGETOOL}"
    chmod +x "${APPIMAGETOOL}"
fi

MINIFORGE="${TOOLS_DIR}/Miniforge3-Linux-${ARCH}.sh"
if [ ! -f "${MINIFORGE}" ]; then
    echo "==> Downloading Miniforge..."
    curl -fSL "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-${ARCH}.sh" \
        -o "${MINIFORGE}"
fi

# ---------------------------------------------------------------------------
# 2. Create conda environment inside AppDir/usr
# ---------------------------------------------------------------------------
echo "==> Creating conda environment at ${APPDIR}/usr ..."
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}"

# Install Miniforge to a temporary location, then create the target env
CONDA_ROOT="${BUILD_DIR}/miniforge"
if [ ! -d "${CONDA_ROOT}" ]; then
    bash "${MINIFORGE}" -b -p "${CONDA_ROOT}" > /dev/null
fi

# Use --copy so all files are real copies (no hardlinks across filesystems)
"${CONDA_ROOT}/bin/mamba" create -y -p "${APPDIR}/usr" --copy \
    -c conda-forge \
    "python=${PYTHON_VERSION}" \
    gdal \
    libgdal \
    proj \
    geos \
    libspatialite \
    pyproj \
    "numpy<2" \
    pandas \
    requests \
    tqdm \
    beautifulsoup4 \
    geopy \
    owslib \
    python-dateutil \
    traitlets \
    laspy \
    lazrs-python \
    p7zip \
    unzip \
    certifi \
    ca-certificates

# ---------------------------------------------------------------------------
# 3. Install pure-Python / pip-only packages
# ---------------------------------------------------------------------------
echo "==> Installing pip packages..."
# curl_cffi is required by the GeoScienceWorld content provider (TLS-impersonation
# fetch for Cloudflare-protected pages); without it, ``import geoextent`` fails
# at content_providers/__init__.py.
"${APPDIR}/usr/bin/pip" install --no-cache-dir \
    geojson "geojsonio" pygeoj pyshp \
    pangaeapy osfclient filesizelib \
    "setuptools-scm>=8" python-dotenv humanfriendly \
    crossref-commons datacite patool wheel \
    curl_cffi

# ---------------------------------------------------------------------------
# 4. Install geoextent itself (no deps — already satisfied above)
# ---------------------------------------------------------------------------
echo "==> Installing geoextent..."
SETUPTOOLS_SCM_PRETEND_VERSION="${GEOEXTENT_VERSION}" \
    "${APPDIR}/usr/bin/pip" install --no-cache-dir --no-deps "${PROJECT_DIR}"

# Verify it imports
"${APPDIR}/usr/bin/python" -c "import geoextent; print('geoextent OK')"

# ---------------------------------------------------------------------------
# 5. Strip unnecessary files to reduce image size
# ---------------------------------------------------------------------------
echo "==> Stripping unnecessary files..."

# Remove conda/mamba/pip infrastructure
rm -rf "${APPDIR}/usr/conda-meta"
rm -rf "${APPDIR}/usr/bin/conda" "${APPDIR}/usr/bin/mamba" "${APPDIR}/usr/bin/pip"* "${APPDIR}/usr/bin/activate"
rm -rf "${APPDIR}/usr/compiler_compat"

# Remove headers, static libs, cmake, pkg-config
rm -rf "${APPDIR}/usr/include"
find "${APPDIR}/usr/lib" -name "*.a" -delete 2>/dev/null || true
rm -rf "${APPDIR}/usr/lib/cmake" "${APPDIR}/usr/lib/pkgconfig"
rm -rf "${APPDIR}/usr/share/cmake" "${APPDIR}/usr/share/pkgconfig"

# Remove documentation and man pages
rm -rf "${APPDIR}/usr/share/man" "${APPDIR}/usr/share/doc" "${APPDIR}/usr/share/info"
rm -rf "${APPDIR}/usr/share/gtk-doc"

# Remove __pycache__ directories
find "${APPDIR}/usr" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Remove Jupyter/IPython if pulled in
rm -rf "${APPDIR}/usr/share/jupyter"
rm -rf "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages/IPython"
rm -rf "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages/jupyter"*

# Remove test directories from site-packages
find "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages" -type d -name "test" -exec rm -rf {} + 2>/dev/null || true

# Strip debug symbols from shared libraries
find "${APPDIR}/usr/lib" -name "*.so*" -exec strip --strip-debug {} \; 2>/dev/null || true

# ---------------------------------------------------------------------------
# 6. Assemble AppDir root (AppRun, .desktop, icon)
# ---------------------------------------------------------------------------
echo "==> Assembling AppDir..."

# Copy AppRun and replace version placeholder
cp "${PROJECT_DIR}/appimage/AppRun" "${APPDIR}/AppRun"
chmod +x "${APPDIR}/AppRun"
sed -i "s/__GEOEXTENT_VERSION__/${GEOEXTENT_VERSION}/g" "${APPDIR}/AppRun"

# Desktop entry
cp "${PROJECT_DIR}/appimage/geoextent.desktop" "${APPDIR}/geoextent.desktop"

# Icon (AppImage spec requires a PNG in the root)
ICON_SRC="${PROJECT_DIR}/docs/source/_static/geoextent-logo-only.png"
if [ -f "${ICON_SRC}" ]; then
    cp "${ICON_SRC}" "${APPDIR}/geoextent.png"
else
    # Create a minimal 1x1 placeholder if the logo is missing
    echo "Warning: Logo not found at ${ICON_SRC}, using placeholder"
    convert -size 64x64 xc:blue "${APPDIR}/geoextent.png" 2>/dev/null || \
        printf '\x89PNG\r\n\x1a\n' > "${APPDIR}/geoextent.png"
fi

# ---------------------------------------------------------------------------
# 7. Build the AppImage
# ---------------------------------------------------------------------------
echo "==> Building AppImage with zstd compression..."

OUTPUT_NAME="geoextent-${GEOEXTENT_VERSION}-${ARCH}.AppImage"

# appimagetool needs FUSE or --appimage-extract-and-run fallback
export ARCH
APPIMAGETOOL_FLAGS="--comp zstd"

"${APPIMAGETOOL}" ${APPIMAGETOOL_FLAGS} "${APPDIR}" "${PROJECT_DIR}/${OUTPUT_NAME}" \
    || "${APPIMAGETOOL}" --appimage-extract-and-run ${APPIMAGETOOL_FLAGS} "${APPDIR}" "${PROJECT_DIR}/${OUTPUT_NAME}"

echo ""
echo "==> AppImage built successfully:"
ls -lh "${PROJECT_DIR}/${OUTPUT_NAME}"
echo ""
echo "Test it with:"
echo "  ./${OUTPUT_NAME} --version"
echo "  ./${OUTPUT_NAME} -b tests/testdata/tif/wf_100m_klas.tif"
