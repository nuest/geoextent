# README Reduction Plan

## Current State
The README.md is **~800 lines** with extensive documentation covering all features, examples, and use cases.

## Proposed State
Reduce README to **~200-250 lines** focusing on quick start and essential information, with comprehensive details moved to documentation.

---

## Content to KEEP in README (Essential)

### 1. Project Header & Badges (Lines 1-10)
**Keep as-is** - Essential project identification

### 2. Brief Introduction (New - ~10 lines)
```markdown
# geoextent

Python library for extracting geospatial extent of files and directories with multiple data formats.

**Key Features:**
- Extract spatial (bounding box/convex hull) and temporal extents
- Support for 9+ file formats (GeoJSON, CSV, Shapefile, GeoTIFF, etc.)
- Direct integration with 8 research repositories (Zenodo, PANGAEA, OSF, Figshare, Dryad, GFZ, Dataverse, Pensoft)
- Command-line interface and Python API
- Docker support for easy deployment

[📖 Full Documentation](https://nuest.github.io/geoextent/) | [📦 PyPI](https://pypi.org/project/geoextent/)
```

### 3. API Stability Note (Lines 11-28)
**Keep** - Important for users to understand breaking changes

### 4. Quick Installation (Simplified - ~20 lines)
```markdown
## Installation

### Requirements
- Python 3.10+
- GDAL 3.11.x

### Install from PyPI
\`\`\`bash
pip install geoextent
\`\`\`

### Install from Source
\`\`\`bash
git clone https://github.com/nuest/geoextent
cd geoextent
pip install -e .[dev,test,docs]
\`\`\`

For detailed installation instructions including system dependencies, see the [installation guide](docs-link).
```

### 5. Quick Start Examples (Simplified - ~40 lines)
```markdown
## Quick Start

### Basic Usage

\`\`\`bash
# Extract bounding box from a file
python -m geoextent -b tests/testdata/geojson/muenster_ring_zeit.geojson

# Extract both spatial and temporal extents
python -m geoextent -b -t tests/testdata/csv/cities_NL.csv

# Extract from research repository
python -m geoextent -b -t https://doi.org/10.5281/zenodo.4593540
\`\`\`

### Python API

\`\`\`python
import geoextent.lib.extent as geoextent

# From file
result = geoextent.fromFile('data.geojson', bbox=True, tbox=True)

# From directory
result = geoextent.fromDirectory('data/', bbox=True, tbox=True)

# From repository
result = geoextent.fromRemote('10.5281/zenodo.4593540', bbox=True, tbox=True)
\`\`\`

For comprehensive examples and advanced features, see the [examples documentation](docs-link).
```

### 6. Supported Formats (Condensed - ~10 lines)
```markdown
## Supported Formats

**Data Formats:** GeoJSON, CSV, Shapefile, GeoTIFF, GeoPackage, GPX, GML, KML, FlatGeobuf

**Repositories:** Zenodo, PANGAEA, OSF, Figshare, Dryad, GFZ Data Services, Dataverse, Pensoft

See [full format documentation](docs-link) for details.
```

### 7. Development Essentials (Simplified - ~30 lines)
```markdown
## Development

### Running Tests
\`\`\`bash
pytest
\`\`\`

### Code Formatting
\`\`\`bash
black geoextent/ tests/
pre-commit install
\`\`\`

### Building Documentation
\`\`\`bash
pip install -e .[docs]
cd docs && make html
\`\`\`

See [development guide](docs-link) for detailed instructions including local CI testing.
```

### 8. Contributing, Citation, License (Lines 745-765)
**Keep as-is** - Essential community information

---

## Content to MOVE to Documentation

### → Move to `docs/source/examples.rst` (Already done ✓)
- **Lines 124-200**: All Docker examples (keep 2-3 basic ones in README)
- **Lines 200-442**: Detailed placename lookup examples
- **Lines 315-402**: Download size limiting examples
- **Lines 404-447**: Performance and filtering options
- **Lines 449-505**: Output format examples
- **Lines 507-536**: Repository extraction options
- **Lines 538-567**: Convex hull details
- **Lines 640-661**: Showcases section

### → Move to `docs/source/install.rst` (Update needed)
- **Lines 30-67**: Detailed system requirements
- **Lines 69-123**: Docker installation details (keep brief mention in README)

### → Move to `docs/source/howto/cli.rst` (Update needed)
- **Lines 126-196**: All CLI flag details (keep 3-5 basic examples)

### → Move to `docs/source/development.rst` (Already exists)
- **Lines 684-744**: Detailed testing instructions
- Local CI testing with act (already documented)

### → Move to New `docs/source/features.rst`
Create comprehensive features page covering:
- Placename lookup (with all gazetteer options)
- Size limiting strategies
- File filtering
- Output formats
- Convex hull vs bounding box
- Quiet mode and scripting
- Performance optimization

---

## Line-by-Line Reduction Strategy

### Delete Entirely (Move to docs)
- Lines 201-246: Placename lookup detailed examples → `examples.rst`
- Lines 248-304: Placename setup details → `features.rst`
- Lines 315-402: Size limiting detailed examples → `examples.rst`
- Lines 404-447: Performance options → `features.rst`
- Lines 449-505: Output formats → `features.rst`
- Lines 507-536: Repository options → `examples.rst`
- Lines 538-567: Convex hull examples → `features.rst`
- Lines 569-639: Output examples → `examples.rst`
- Lines 640-661: Showcases → Keep link, move details to docs

### Condense to 1-2 lines (with docs link)
- Lines 69-123: Docker usage → "Docker images available, see [Docker guide](docs-link)"
- Lines 474-505: Quiet mode → One example + docs link

---

## Proposed New README Structure (~220 lines)

1. **Header & Badges** (10 lines)
2. **Brief Introduction** (15 lines) - NEW
3. **API Stability** (15 lines) - Keep
4. **Quick Installation** (25 lines) - Simplified
5. **Quick Start** (50 lines) - Simplified examples
6. **Docker** (10 lines) - Just mention + link
7. **Supported Formats** (12 lines) - List only
8. **Development** (35 lines) - Essentials only
9. **Contributing** (10 lines) - Keep
10. **Citation** (5 lines) - Keep
11. **License** (3 lines) - Keep

**Total: ~200-220 lines** (73% reduction from 800 lines)

---

## Documentation Structure (Enhanced)

\`\`\`
docs/
├── source/
│   ├── index.rst              # Main entry point
│   ├── install.rst            # Detailed installation (enhanced)
│   ├── examples.rst           # Comprehensive examples (✓ created)
│   ├── features.rst           # Feature documentation (to create)
│   ├── howto/
│   │   ├── api.rst           # Python API guide
│   │   ├── cli.rst           # CLI guide (✓ updated)
│   │   └── docker.rst        # Docker guide (to create)
│   ├── supportedformats/      # Format details
│   ├── changelog.rst          # Version history
│   └── development.rst        # Development guide
\`\`\`

---

## Migration Checklist

- [x] Create `docs/source/examples.rst` with <100MB examples
- [x] Update `docs/source/howto/cli.rst` with repository examples
- [x] Add documentation build instructions to README
- [x] Update documentation workflow for Sphinx 8+
- [ ] Create `docs/source/features.rst` (if time permits)
- [ ] Create `docs/source/howto/docker.rst` (if time permits)
- [ ] Update `docs/source/install.rst` with system dependencies
- [ ] Reduce README.md to ~220 lines
- [ ] Update all README doc links to point to correct pages
- [ ] Test all documentation builds in CI

---

## Benefits of This Approach

1. **Easier Onboarding**: New users see essential info immediately
2. **Better Maintainability**: Detailed examples in one place (docs)
3. **Improved Searchability**: Comprehensive docs are easier to search
4. **Version Control**: Docs can be versioned with releases
5. **Reduced README Scroll**: From 800 lines to ~220 lines
6. **Clear Separation**: README = "What & Why", Docs = "How & Details"

---

## Example Datasets Selected (<100MB)

All examples use these carefully chosen datasets:

| Provider | DOI/URL | Size | Content |
|----------|---------|------|---------|
| Zenodo | 10.5281/zenodo.4593540 | ~50MB | Atmospheric data, multiple formats |
| PANGAEA | 10.1594/PANGAEA.734969 | ~1MB | Arctic Ocean, rich metadata |
| OSF | 10.17605/OSF.IO/4XE6Z | ~5MB | Geographic research, multiple files |
| GFZ | 10.5880/GFZ.4.8.2023.004 | ~30MB | Geothermal resources, GeoTIFF |

These cover:
- ✅ All major repository providers
- ✅ Multiple file formats (CSV, GeoJSON, GeoTIFF, Shapefile)
- ✅ Both spatial and temporal extents
- ✅ Fast download/processing times
- ✅ Real scientific datasets
