#!/usr/bin/env python3
"""
Build script for packaging geoextent as a WebAssembly module using Pyodide.

This script prepares the geoextent package for use in web browsers by:
1. Creating a minimal package build optimized for Pyodide
2. Generating dependency lists for Pyodide and micropip
3. Creating configuration files for the web interface
"""

import json
import shutil
import os
import sys
from pathlib import Path

def load_config():
    """Load the Pyodide configuration."""
    config_path = Path(__file__).parent / "pyodide-config.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def prepare_package_directory(config):
    """Prepare the package directory for web deployment."""
    # Get the project root (parent of web directory)
    project_root = Path(__file__).parent.parent
    build_dir = Path(__file__).parent / "build"

    # Clean and create build directory
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    # Copy geoextent package
    geoextent_src = project_root / "geoextent"
    geoextent_dst = build_dir / "geoextent"

    if geoextent_src.exists():
        shutil.copytree(geoextent_src, geoextent_dst,
                       ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'tests'))
        print(f"Copied geoextent package to {geoextent_dst}")
    else:
        print(f"Warning: geoextent source directory not found at {geoextent_src}")

    # Copy essential files
    essential_files = ['README.md', 'LICENSE']
    for file_name in essential_files:
        src_file = project_root / file_name
        if src_file.exists():
            shutil.copy2(src_file, build_dir / file_name)
            print(f"Copied {file_name}")

    return build_dir

def generate_package_metadata(config, build_dir):
    """Generate package metadata for Pyodide."""
    metadata = {
        "name": config["name"],
        "version": config["version"],
        "description": config["description"],
        "dependencies": config["dependencies"],
        "files": []
    }

    # List all Python files in the build
    for py_file in build_dir.rglob("*.py"):
        relative_path = py_file.relative_to(build_dir)
        metadata["files"].append(str(relative_path))

    metadata_path = build_dir / "package-metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Generated metadata: {len(metadata['files'])} files")
    return metadata

def create_pyodide_loader(config, build_dir):
    """Create a JavaScript loader for Pyodide initialization."""
    loader_js = f'''
/**
 * Geoextent WebAssembly Loader
 * Initializes Pyodide and loads the geoextent package
 */

class GeoextentWasm {{
    constructor() {{
        this.pyodide = null;
        this.initialized = false;
        this.loading = false;
    }}

    async initialize(progressCallback = null) {{
        if (this.initialized) return this.pyodide;
        if (this.loading) {{
            // Wait for current initialization to complete
            while (this.loading) {{
                await new Promise(resolve => setTimeout(resolve, 100));
            }}
            return this.pyodide;
        }}

        this.loading = true;

        try {{
            if (progressCallback) progressCallback("Loading Pyodide...");

            // Load Pyodide
            this.pyodide = await loadPyodide({{
                indexURL: "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/"
            }});

            if (progressCallback) progressCallback("Installing packages...");

            // Install Pyodide packages (GDAL, etc.)
            const pyodide_packages = {json.dumps(config["dependencies"]["pyodide_packages"])};
            if (pyodide_packages.length > 0) {{
                await this.pyodide.loadPackage(pyodide_packages);
            }}

            // Install micropip packages
            const micropip_packages = {json.dumps(config["dependencies"]["micropip_packages"])};
            if (micropip_packages.length > 0) {{
                await this.pyodide.loadPackage("micropip");
                const micropip = this.pyodide.pyimport("micropip");
                for (const pkg of micropip_packages) {{
                    try {{
                        await micropip.install(pkg);
                    }} catch (e) {{
                        console.warn(`Failed to install ${{pkg}}:`, e);
                    }}
                }}
            }}

            if (progressCallback) progressCallback("Loading geoextent...");

            // Load the geoextent package
            await this.loadGeoextentPackage();

            this.initialized = true;
            if (progressCallback) progressCallback("Ready!");

            return this.pyodide;

        }} catch (error) {{
            console.error("Failed to initialize Pyodide:", error);
            if (progressCallback) progressCallback("Error loading Pyodide");
            throw error;
        }} finally {{
            this.loading = false;
        }}
    }}

    async loadGeoextentPackage() {{
        // Load the geoextent package files
        const response = await fetch('./build/geoextent/__init__.py');
        const initPy = await response.text();

        // Create the package structure in Pyodide's filesystem
        this.pyodide.FS.mkdir('/geoextent');
        this.pyodide.FS.writeFile('/geoextent/__init__.py', initPy);

        // Load all Python modules recursively
        await this.loadPythonModules('/geoextent', './build/geoextent');
    }}

    async loadPythonModules(targetPath, sourcePath) {{
        try {{
            // Get list of files in the build directory
            const response = await fetch(`${{sourcePath}}/package-metadata.json`);
            if (!response.ok) {{
                console.warn('Could not load package metadata, using fallback module loading');
                await this.loadFallbackModules();
                return;
            }}

            const metadata = await response.json();
            const files = metadata.files || [];

            for (const file of files) {{
                if (file.endsWith('.py')) {{
                    try {{
                        const fileResponse = await fetch(`${{sourcePath}}/${{file}}`);
                        if (fileResponse.ok) {{
                            const content = await fileResponse.text();
                            const fullPath = `${{targetPath}}/${{file}}`;
                            const dir = fullPath.substring(0, fullPath.lastIndexOf('/'));

                            // Create directory structure
                            this.createDirectories(dir);

                            // Write the file
                            this.pyodide.FS.writeFile(fullPath, content);
                        }}
                    }} catch (e) {{
                        console.warn(`Failed to load module ${{file}}:`, e);
                    }}
                }}
            }}
        }} catch (e) {{
            console.warn('Failed to load modules from metadata:', e);
            await this.loadFallbackModules();
        }}
    }}

    createDirectories(path) {{
        const parts = path.split('/').filter(p => p);
        let currentPath = '';

        for (const part of parts) {{
            currentPath += '/' + part;
            try {{
                this.pyodide.FS.mkdir(currentPath);
            }} catch (e) {{
                // Directory might already exist, ignore error
            }}
        }}
    }}

    async loadFallbackModules() {{
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

        for (const module of modules) {{
            try {{
                const response = await fetch(`./build/geoextent/${{module}}`);
                if (response.ok) {{
                    const content = await response.text();
                    const fullPath = `/geoextent/${{module}}`;
                    const dir = fullPath.substring(0, fullPath.lastIndexOf('/'));

                    // Create directory structure
                    this.createDirectories(dir);

                    // Write the file
                    this.pyodide.FS.writeFile(fullPath, content);
                }}
            }} catch (e) {{
                console.warn(`Failed to load fallback module ${{module}}:`, e);
            }}
        }}

        // Add to Python path
        this.pyodide.runPython(`
import sys
sys.path.insert(0, '/')
import geoextent
`);
    }}

    async extractExtent(url, options = {{}}) {{
        if (!this.initialized) {{
            throw new Error("Geoextent WASM not initialized. Call initialize() first.");
        }}

        const defaultOptions = {{
            bbox: true,
            tbox: false,
            format: "geojson",
            timeout: 30000
        }};

        const finalOptions = {{ ...defaultOptions, ...options }};

        try {{
            // Prepare Python code for extraction
            const pythonCode = `
import geoextent.lib.extent as extent
import json

url = "${{url}}"
options = ${{JSON.stringify(finalOptions)}}

try:
    if url.startswith(('http://', 'https://')):
        # Repository URL
        result = extent.from_repository(
            url,
            bbox=options.get('bbox', True),
            tbox=options.get('tbox', False)
        )
    else:
        # Local file (not supported in browser)
        raise ValueError("Local file processing not supported in browser environment")

    # Convert result to JSON-serializable format
    if result:
        json.dumps(result)  # This will be the return value
    else:
        json.dumps({{"error": "No result returned"}})

except Exception as e:
    json.dumps({{"error": str(e), "type": type(e).__name__}})
`;

            const result = this.pyodide.runPython(pythonCode);
            return JSON.parse(result);

        }} catch (error) {{
            console.error("Error in extractExtent:", error);
            return {{ error: error.message, type: "JavaScriptError" }};
        }}
    }}
}}

// Global instance
window.geoextentWasm = new GeoextentWasm();
'''

    loader_path = Path(__file__).parent / "assets" / "js" / "geoextent-loader.js"
    loader_path.parent.mkdir(parents=True, exist_ok=True)

    with open(loader_path, 'w') as f:
        f.write(loader_js)

    print(f"Created Pyodide loader at {loader_path}")

def main():
    """Main build process."""
    print("Building geoextent WebAssembly package...")

    # Load configuration
    config = load_config()

    # Prepare package directory
    build_dir = prepare_package_directory(config)

    # Generate metadata
    metadata = generate_package_metadata(config, build_dir)

    # Create Pyodide loader
    create_pyodide_loader(config, build_dir)

    print(f"\\nBuild completed successfully!")
    print(f"Build directory: {build_dir}")
    print(f"Package files: {len(metadata['files'])}")
    print(f"Dependencies: {len(config['dependencies']['pyodide_packages']) + len(config['dependencies']['micropip_packages'])}")

if __name__ == "__main__":
    main()