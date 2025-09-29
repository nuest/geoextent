#!/bin/bash
#
# Geoextent Web Dependencies Setup Script
#
# This script downloads and sets up all required dependencies for the geoextent web application:
# - Pyodide (WebAssembly Python runtime)
# - Bootstrap (CSS framework)
# - Leaflet (Interactive maps)
# - Font Awesome (Icons)
#
# Usage: ./setup-dependencies.sh
#

set -e  # Exit on any error

# Configuration
PYODIDE_VERSION="0.24.1"
BOOTSTRAP_VERSION="5.3.0"
LEAFLET_VERSION="1.9.4"
FONTAWESOME_VERSION="6.4.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the correct directory
if [ ! -f "index.html" ]; then
    print_error "Please run this script from the web/ directory"
    exit 1
fi

print_status "Setting up geoextent web dependencies..."
print_status "This will create/recreate the assets/lib directory with all required dependencies"

# Create directory structure
print_status "Creating directory structure..."
rm -rf assets/lib
mkdir -p assets/lib/{pyodide,bootstrap,leaflet,fontawesome/webfonts}

# Download Pyodide files
print_status "Downloading Pyodide ${PYODIDE_VERSION}..."
PYODIDE_BASE_URL="https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full"

print_status "  - Downloading pyodide.js..."
wget -q -P assets/lib/pyodide/ "${PYODIDE_BASE_URL}/pyodide.js"

print_status "  - Downloading pyodide.asm.js..."
wget -q -P assets/lib/pyodide/ "${PYODIDE_BASE_URL}/pyodide.asm.js"

print_status "  - Downloading pyodide.asm.wasm..."
wget -q -P assets/lib/pyodide/ "${PYODIDE_BASE_URL}/pyodide.asm.wasm"

print_status "  - Downloading Python standard library..."
wget -q -P assets/lib/pyodide/ "${PYODIDE_BASE_URL}/python_stdlib.zip"

print_status "  - Downloading package metadata..."
wget -q -P assets/lib/pyodide/ "${PYODIDE_BASE_URL}/pyodide-lock.json"

print_status "  - Downloading GDAL package..."
wget -q -P assets/lib/pyodide/ "${PYODIDE_BASE_URL}/gdal-3.5.1.zip"

print_success "Pyodide setup complete"

# Download Bootstrap
print_status "Downloading Bootstrap ${BOOTSTRAP_VERSION}..."
BOOTSTRAP_URL="https://cdn.jsdelivr.net/npm/bootstrap@${BOOTSTRAP_VERSION}/dist"

print_status "  - Downloading Bootstrap CSS..."
wget -q -P assets/lib/bootstrap/ "${BOOTSTRAP_URL}/css/bootstrap.min.css"

print_status "  - Downloading Bootstrap JS..."
wget -q -P assets/lib/bootstrap/ "${BOOTSTRAP_URL}/js/bootstrap.bundle.min.js"

print_success "Bootstrap setup complete"

# Download Leaflet
print_status "Downloading Leaflet ${LEAFLET_VERSION}..."
LEAFLET_URL="https://unpkg.com/leaflet@${LEAFLET_VERSION}/dist"

print_status "  - Downloading Leaflet CSS..."
wget -q -P assets/lib/leaflet/ "${LEAFLET_URL}/leaflet.css"

print_status "  - Downloading Leaflet JS..."
wget -q -P assets/lib/leaflet/ "${LEAFLET_URL}/leaflet.js"

# Download Leaflet images
print_status "  - Downloading Leaflet images..."
mkdir -p assets/lib/leaflet/images
LEAFLET_IMAGES=("layers.png" "layers-2x.png" "marker-icon.png" "marker-icon-2x.png" "marker-shadow.png")
for img in "${LEAFLET_IMAGES[@]}"; do
    wget -q -P assets/lib/leaflet/images/ "${LEAFLET_URL}/images/${img}"
done

print_success "Leaflet setup complete"

# Download Font Awesome
print_status "Downloading Font Awesome ${FONTAWESOME_VERSION}..."
FONTAWESOME_URL="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/${FONTAWESOME_VERSION}"

print_status "  - Downloading Font Awesome CSS..."
wget -q -P assets/lib/fontawesome/ "${FONTAWESOME_URL}/css/all.min.css"

print_status "  - Downloading Font Awesome fonts..."
FONTAWESOME_FONTS=(
    "fa-solid-900.woff2"
    "fa-solid-900.ttf"
    "fa-regular-400.woff2"
    "fa-regular-400.ttf"
    "fa-brands-400.woff2"
    "fa-brands-400.ttf"
)

for font in "${FONTAWESOME_FONTS[@]}"; do
    wget -q -P assets/lib/fontawesome/webfonts/ "${FONTAWESOME_URL}/webfonts/${font}"
done

# Create a symlink for easier access from CSS
ln -sf fontawesome/webfonts assets/lib/webfonts

print_success "Font Awesome setup complete"

# Create a summary file
print_status "Creating dependency summary..."
cat > assets/lib/README.md << 'EOF'
# Web Dependencies

This directory contains all external dependencies for the geoextent web application.

## Contents

- **pyodide/**: Python runtime for WebAssembly
  - Core Pyodide files and GDAL package
  - Version: 0.24.1
  - Includes GDAL 3.5.1 for geospatial processing

- **bootstrap/**: CSS framework for responsive design
  - Version: 5.3.0
  - Includes CSS and JavaScript bundle

- **leaflet/**: Interactive maps library
  - Version: 1.9.4
  - Includes CSS, JavaScript, and image assets

- **fontawesome/**: Icon font library
  - Version: 6.4.0
  - Includes CSS and web fonts (WOFF2, TTF formats)

- **webfonts/**: Symlink to fontawesome/webfonts for CSS compatibility

## Regenerating Dependencies

To recreate this directory, run:
```bash
cd web/
./setup-dependencies.sh
```

## File Sizes (Approximate)

- Pyodide: ~35MB (includes GDAL package)
- Bootstrap: ~200KB
- Leaflet: ~150KB + images
- Font Awesome: ~1.5MB (fonts + CSS)

**Total: ~37MB**
EOF

# Display summary
print_success "Web dependencies setup complete!"
echo
print_status "Summary:"
echo "  ✓ Pyodide ${PYODIDE_VERSION} with GDAL support"
echo "  ✓ Bootstrap ${BOOTSTRAP_VERSION}"
echo "  ✓ Leaflet ${LEAFLET_VERSION}"
echo "  ✓ Font Awesome ${FONTAWESOME_VERSION}"
echo
print_status "Directory structure:"
find assets/lib -type f | head -20
if [ $(find assets/lib -type f | wc -l) -gt 20 ]; then
    echo "  ... and $(( $(find assets/lib -type f | wc -l) - 20 )) more files"
fi
echo
print_status "Total size: $(du -sh assets/lib | cut -f1)"
echo
print_success "You can now start the web server with: python serve.py"