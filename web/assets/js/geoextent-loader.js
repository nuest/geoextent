
/**
 * Geoextent WebAssembly Loader
 * Initializes Pyodide and loads the geoextent package
 */

class GeoextentWasm {
    constructor() {
        this.pyodide = null;
        this.initialized = false;
        this.loading = false;
    }

    async initialize(progressCallback = null) {
        if (this.initialized) return this.pyodide;
        if (this.loading) {
            // Wait for current initialization to complete
            while (this.loading) {
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            return this.pyodide;
        }

        this.loading = true;

        try {
            if (progressCallback) progressCallback("Loading Pyodide...");

            // Load Pyodide from local files
            this.pyodide = await loadPyodide({
                indexURL: "./assets/lib/pyodide/"
            });

            if (progressCallback) progressCallback("Installing packages...");

            // Debug: Check what packages are available in this Pyodide version
            const availablePackages = this.pyodide.runPython(`
import pyodide_js
available = list(pyodide_js.packages.dependencies.object_keys())
gdal_available = 'gdal' in available
f"Available packages: {len(available)}, GDAL available: {gdal_available}"
`);
            console.log("Pyodide package availability:", availablePackages);

            // Try multiple approaches to get GDAL working
            if (progressCallback) progressCallback("Loading GDAL (core dependency)...");

            // First, load micropip for alternative GDAL installation
            await this.pyodide.loadPackage("micropip");
            const micropip = this.pyodide.pyimport("micropip");

            let gdalWorking = false;
            let gdalError = "";

            // Approach 1: Try loadPackage first
            try {
                const hasGdal = this.pyodide.runPython(`
import pyodide_js
'gdal' in list(pyodide_js.packages.dependencies.object_keys())
`);

                if (hasGdal) {
                    console.log("Attempting to load GDAL via loadPackage...");
                    await this.pyodide.loadPackage("gdal");

                    const gdalTest = this.pyodide.runPython(`
try:
    from osgeo import gdal, ogr, osr
    f"GDAL version: {gdal.__version__}"
except Exception as e:
    f"failed: {str(e)}"
`);

                    if (!gdalTest.includes("failed")) {
                        console.log("GDAL loaded successfully via loadPackage:", gdalTest);
                        gdalWorking = true;
                    } else {
                        gdalError = gdalTest;
                    }
                }
            } catch (e) {
                console.log("loadPackage approach failed:", e.message);
                gdalError = e.message;
            }

            // Approach 2: Try micropip if loadPackage failed
            if (!gdalWorking) {
                try {
                    console.log("Attempting to install GDAL via micropip...");
                    await micropip.install("gdal");

                    const gdalTest = this.pyodide.runPython(`
try:
    from osgeo import gdal, ogr, osr
    f"GDAL version: {gdal.__version__}"
except Exception as e:
    f"failed: {str(e)}"
`);

                    if (!gdalTest.includes("failed")) {
                        console.log("GDAL loaded successfully via micropip:", gdalTest);
                        gdalWorking = true;
                    } else {
                        gdalError += " | micropip: " + gdalTest;
                    }
                } catch (e) {
                    console.log("micropip approach failed:", e.message);
                    gdalError += " | micropip error: " + e.message;
                }
            }

            if (!gdalWorking) {
                console.error("All GDAL loading approaches failed:", gdalError);
                if (progressCallback) progressCallback(`GDAL Error: Cannot load GDAL/osgeo`);
                throw new Error(`GDAL is required but failed to load. Tried loadPackage and micropip. Errors: ${gdalError}`);
            }

            // Load other geospatial packages if GDAL is working
            if (progressCallback) progressCallback("Loading additional geospatial packages...");
            const additional_packages = ["geopandas", "fiona"];
            for (const pkg of additional_packages) {
                try {
                    console.log(`Loading ${pkg}...`);
                    await this.pyodide.loadPackage(pkg);
                    console.log(`Successfully loaded ${pkg}`);
                } catch (e) {
                    console.warn(`Failed to load ${pkg} (optional):`, e);
                }
            }

            // Install micropip packages (micropip already loaded for GDAL)
            if (progressCallback) progressCallback("Installing Python packages...");
            const micropip_packages = ["pyproj", "geojson>=2.4.1", "pyshp", "patool", "python-dateutil", "pandas", "numpy<2", "requests", "traitlets", "tqdm"];
            // Note: pangaeapy requires pandas>=2.2.2 but Pyodide only has pandas 1.5.3, so we skip it
            const optional_packages = ["pygeoj", "wheel", "osfclient"];

            // Install required packages
            for (const pkg of micropip_packages) {
                try {
                    await micropip.install(pkg);
                    console.log(`Successfully installed ${pkg}`);
                } catch (e) {
                    console.warn(`Failed to install ${pkg}:`, e);
                }
            }

            // Try to install optional packages (don't fail if they don't work)
            for (const pkg of optional_packages) {
                try {
                    await micropip.install(pkg);
                    console.log(`Successfully installed optional ${pkg}`);
                } catch (e) {
                    console.warn(`Optional package ${pkg} failed to install (skipping):`, e);
                }
            }

            if (progressCallback) progressCallback("Loading geoextent...");

            // Load the geoextent package
            await this.loadGeoextentPackage();

            this.initialized = true;
            if (progressCallback) progressCallback("Ready!");

            return this.pyodide;

        } catch (error) {
            console.error("Failed to initialize Pyodide:", error);
            if (progressCallback) progressCallback("Error loading Pyodide");
            throw error;
        } finally {
            this.loading = false;
        }
    }

    async loadGeoextentPackage() {
        // Load the geoextent package files
        const response = await fetch('./build/geoextent/__init__.py');
        const initPy = await response.text();

        // Create the package structure in Pyodide's filesystem
        this.pyodide.FS.mkdir('/geoextent');
        this.pyodide.FS.writeFile('/geoextent/__init__.py', initPy);

        // Load all Python modules recursively
        await this.loadPythonModules('/geoextent', './build/geoextent');
    }

    async loadPythonModules(targetPath, sourcePath) {
        try {
            // Get list of files in the build directory
            const response = await fetch(`${sourcePath}/package-metadata.json`);
            if (!response.ok) {
                console.warn('Could not load package metadata, using fallback module loading');
                await this.loadFallbackModules();
                return;
            }

            const metadata = await response.json();
            const files = metadata.files || [];

            for (const file of files) {
                if (file.endsWith('.py')) {
                    try {
                        const fileResponse = await fetch(`${sourcePath}/${file}`);
                        if (fileResponse.ok) {
                            const content = await fileResponse.text();
                            const fullPath = `${targetPath}/${file}`;
                            const dir = fullPath.substring(0, fullPath.lastIndexOf('/'));

                            // Create directory structure
                            this.createDirectories(dir);

                            // Write the file
                            this.pyodide.FS.writeFile(fullPath, content);
                        }
                    } catch (e) {
                        console.warn(`Failed to load module ${file}:`, e);
                    }
                }
            }
        } catch (e) {
            console.warn('Failed to load modules from metadata:', e);
            await this.loadFallbackModules();
        }
    }

    createDirectories(path) {
        const parts = path.split('/').filter(p => p);
        let currentPath = '';

        for (const part of parts) {
            currentPath += '/' + part;
            try {
                this.pyodide.FS.mkdir(currentPath);
            } catch (e) {
                // Directory might already exist, ignore error
            }
        }
    }

    async loadFallbackModules() {
        // Fallback: load essential modules manually
        const modules = [
            'lib/extent.py',
            'lib/helpfunctions.py',
            '__main__.py',
            'lib/content_providers/__init__.py',
            'lib/content_providers/providers.py',
            'lib/content_providers/Zenodo.py',
            'lib/content_providers/Figshare.py',
            'lib/content_providers/Dryad.py',
            'lib/content_providers/Pangaea.py',
            'lib/content_providers/OSF.py',
            'lib/content_providers/Dataverse.py',
            'lib/content_providers/GFZ.py'
        ];

        for (const module of modules) {
            try {
                const response = await fetch(`./build/geoextent/${module}`);
                if (response.ok) {
                    const content = await response.text();
                    const fullPath = `/geoextent/${module}`;
                    const dir = fullPath.substring(0, fullPath.lastIndexOf('/'));

                    // Create directory structure
                    this.createDirectories(dir);

                    // Write the file
                    this.pyodide.FS.writeFile(fullPath, content);
                }
            } catch (e) {
                console.warn(`Failed to load fallback module ${module}:`, e);
            }
        }

        // Add to Python path
        this.pyodide.runPython(`
import sys
sys.path.insert(0, '/')
import geoextent
`);
    }

    async extractExtent(url, options = {}) {
        if (!this.initialized) {
            throw new Error("Geoextent WASM not initialized. Call initialize() first.");
        }

        const defaultOptions = {
            bbox: true,
            tbox: false,
            format: "geojson",
            timeout: 30000
        };

        const finalOptions = { ...defaultOptions, ...options };

        try {
            // Debug: Check what modules are available
            const debugInfo = this.pyodide.runPython(`
import sys
import os
import json

debug_info = {
    "python_path": sys.path,
    "geoextent_files": [],
    "content_providers_files": []
}

# Check geoextent directory
if os.path.exists('/geoextent'):
    debug_info["geoextent_files"] = os.listdir('/geoextent')

    if os.path.exists('/geoextent/lib'):
        debug_info["lib_files"] = os.listdir('/geoextent/lib')

        if os.path.exists('/geoextent/lib/content_providers'):
            debug_info["content_providers_files"] = os.listdir('/geoextent/lib/content_providers')

# Test imports
try:
    import geoextent
    debug_info["geoextent_import"] = "SUCCESS"
except Exception as e:
    debug_info["geoextent_import"] = f"FAILED: {str(e)}"

try:
    import geoextent.lib
    debug_info["geoextent_lib_import"] = "SUCCESS"
except Exception as e:
    debug_info["geoextent_lib_import"] = f"FAILED: {str(e)}"

try:
    import geoextent.lib.content_providers
    debug_info["content_providers_import"] = "SUCCESS"
except Exception as e:
    debug_info["content_providers_import"] = f"FAILED: {str(e)}"

json.dumps(debug_info, indent=2)
`);

            console.log("Debug info:", JSON.parse(debugInfo));

            // Prepare Python code for extraction
            const pythonCode = `
import json
import sys

url = "${url}"
options = ${JSON.stringify(finalOptions)}

try:
    # First ensure content_providers is importable
    try:
        import geoextent.lib.content_providers
    except ImportError as e:
        # Try to add it to sys.modules if files exist
        import os
        if os.path.exists('/geoextent/lib/content_providers'):
            # Create empty module for content_providers
            import types
            cp_module = types.ModuleType('geoextent.lib.content_providers')
            sys.modules['geoextent.lib.content_providers'] = cp_module

    # Now try to import extent
    import geoextent.lib.extent as extent

    if url.startswith(('http://', 'https://')):
        # Repository URL - use a simple test first
        result = {"test": True, "url": url, "message": "Module import successful"}
    else:
        # Local file (not supported in browser)
        raise ValueError("Local file processing not supported in browser environment")

    # Convert result to JSON-serializable format
    json.dumps(result)

except ImportError as e:
    json.dumps({"error": f"Import error: {str(e)}", "type": "ImportError"})
except Exception as e:
    json.dumps({"error": str(e), "type": type(e).__name__})
`;

            const result = this.pyodide.runPython(pythonCode);
            return JSON.parse(result);

        } catch (error) {
            console.error("Error in extractExtent:", error);
            return { error: error.message, type: "JavaScriptError" };
        }
    }
}

// Global instance
window.geoextentWasm = new GeoextentWasm();
