# Geoextent Web - WebAssembly Version

A browser-based version of geoextent that runs entirely in the browser using Pyodide and WebAssembly, enabling geospatial extent extraction without any server or local installation requirements.

## 🌟 Features

- **No Installation Required**: Runs entirely in your web browser
- **Repository Support**: Extract extents from Zenodo, Figshare, Dryad, PANGAEA, OSF, Dataverse, and GFZ
- **Interactive Maps**: Visualize spatial extents using Leaflet maps
- **Multiple Formats**: Output in GeoJSON, WKT, or WKB formats
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Advanced Options**: Size limits, sampling methods, and timeout controls

## 🚀 Quick Start

### Option 1: Use the Hosted Version
Visit the hosted version at: **[Coming Soon]**

### Option 2: Run Locally

1. **Clone the repository**:
   ```bash
   git clone https://github.com/nuest/geoextent.git
   cd geoextent/web
   ```

2. **Set up dependencies**:
   ```bash
   ./setup-dependencies.sh
   ```
   This downloads all required JavaScript libraries, fonts, and the Pyodide WebAssembly runtime (~37MB total).

3. **Start the development server**:
   ```bash
   python serve.py
   ```

4. **Open in your browser**:
   Navigate to `http://localhost:8080`

### Option 3: Use with any HTTP Server

The web application is a static single-page application that can be served by any HTTP server:

```bash
# Using Python's built-in server
python -m http.server 8080

# Using Node.js's http-server
npx http-server -p 8080 -c-1

# Using PHP's built-in server
php -S localhost:8080
```

**⚠️ Important**: Due to browser security restrictions, the application must be served over HTTP(S), not opened as a local file.

## 🖥️ User Interface

### Main Components

1. **URL Input**: Enter repository URLs or DOIs
2. **Basic Options**: Toggle bounding box/temporal extent extraction and output format
3. **Advanced Options**: Configure download size limits, sampling methods, and timeouts
4. **Interactive Map**: View extracted spatial extents on a Leaflet map
5. **Results Panel**: View and copy JSON results

### Supported URL Formats

- **Zenodo**: `https://zenodo.org/record/1234567` or `doi:10.5281/zenodo.1234567`
- **Figshare**: `https://figshare.com/articles/dataset/Title/1234567`
- **Dryad**: `https://datadryad.org/stash/dataset/doi:10.5061/dryad.example`
- **PANGAEA**: `https://doi.pangaea.de/10.1594/PANGAEA.1234567`
- **OSF**: `https://osf.io/abc12/`
- **Dataverse**: `https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/example`
- **GFZ**: `https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=example`

## ⚙️ Configuration Options

### Basic Options

- **Extract Bounding Box**: Extract spatial extent (enabled by default)
- **Extract Temporal Extent**: Extract time range information
- **Output Format**: Choose between GeoJSON, WKT, or WKB

### Advanced Options

- **Max Download Size**: Limit total download size (e.g., "100MB", "1GB")
- **Download Method**: Choose "ordered" (first files) or "random" sampling
- **Timeout**: Set maximum processing time in seconds

## 🛠️ Technical Details

### Architecture

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **UI Framework**: Bootstrap 5.3.2
- **Maps**: Leaflet 1.9.4
- **Icons**: Font Awesome 6.4.0
- **Python Runtime**: Pyodide 0.24.1
- **Geospatial Processing**: GDAL, Geopandas, Fiona (via Pyodide)

### Dependencies

The application automatically loads these Python packages:
- `gdal`, `geopandas`, `fiona` (from Pyodide)
- `pyproj`, `geojson`, `pandas`, `numpy`, `requests` (via micropip)
- Complete list in `pyodide-config.json`

### Browser Compatibility

**Supported Browsers:**
- Chrome/Chromium 87+
- Firefox 78+
- Safari 14+
- Edge 87+

**Requirements:**
- WebAssembly support
- ES6+ JavaScript support
- Minimum 512MB available memory
- Stable internet connection for package downloads

## 🔧 Development

### Project Structure

```
web/
├── index.html              # Main application page
├── assets/
│   ├── css/
│   │   └── style.css       # Custom styles
│   ├── js/
│   │   ├── app.js          # Main application logic
│   │   ├── geoextent-loader.js  # Pyodide integration
│   │   └── map-handler.js  # Leaflet map management
│   └── lib/                # Local libraries (Bootstrap, Leaflet, etc.)
├── build/                  # Generated geoextent package
├── build.py               # Build script
├── serve.py               # Development server
├── pyodide-config.json    # Pyodide configuration
└── README.md              # This file
```

### Building

To rebuild the geoextent package for the web:

```bash
python build.py
```

This script:
1. Copies the geoextent Python package
2. Generates metadata
3. Creates the Pyodide loader script

### Local Development

1. **Set up dependencies** (first time only):
   ```bash
   ./setup-dependencies.sh
   ```

2. **Make changes** to the source code
3. **Rebuild** if you modified the Python package: `python build.py`
4. **Refresh** your browser to see changes

### Dependencies Management

The `setup-dependencies.sh` script manages all external web dependencies:

- **Pyodide 0.24.1**: WebAssembly Python runtime with GDAL support
- **Bootstrap 5.3.0**: CSS framework for responsive design
- **Leaflet 1.9.4**: Interactive maps library
- **Font Awesome 6.4.0**: Icon fonts

To recreate the `assets/lib/` directory:
```bash
rm -rf assets/lib
./setup-dependencies.sh
```

### Adding New Features

1. **UI Changes**: Modify `index.html` and `assets/css/style.css`
2. **Application Logic**: Edit `assets/js/app.js`
3. **Map Features**: Update `assets/js/map-handler.js`
4. **Pyodide Integration**: Modify `assets/js/geoextent-loader.js`

## 🎯 Usage Examples

### Basic Extent Extraction

1. Open the application in your browser
2. Wait for initialization to complete
3. Enter a repository URL: `https://zenodo.org/record/4281387`
4. Click "Extract Extent"
5. View results on the map and in the JSON output

### Advanced Configuration

1. Click "Advanced Options" to expand
2. Set download limit: `50MB`
3. Choose sampling method: `random`
4. Set timeout: `60` seconds
5. Extract extent with these settings

### Copying Results

1. After extraction completes
2. Click "Copy JSON" button in results section
3. Paste into your application or analysis tool

## 🚨 Limitations

### Performance
- **Processing Speed**: Slower than native Python version
- **Memory Usage**: Limited by browser memory constraints
- **File Size**: Large datasets may cause browser freezing

### Functionality
- **CORS Restrictions**: Some URLs may be blocked by browser security
- **Local Files**: Cannot process files from your local computer
- **Network Dependency**: Requires internet connection for package downloads

### Browser-Specific
- **Mobile Browsers**: Limited memory may cause issues with large datasets
- **Private Browsing**: May prevent caching of Pyodide packages
- **Extensions**: Ad blockers may interfere with CDN requests

## 🆚 Differences from Python Package

| Feature | Python Package | Web Version |
|---------|---------------|-------------|
| Installation | Requires setup | No installation |
| Local Files | ✅ Supported | ❌ Not supported |
| Repository URLs | ✅ Supported | ✅ Supported |
| Performance | ⚡ Fast | 🐌 Slower |
| Memory Usage | 💪 Efficient | 📱 Limited |
| Offline Usage | ✅ Yes | ❌ No |
| CLI Interface | ✅ Available | ❌ Web only |
| Batch Processing | ✅ Supported | ❌ Single URLs |

## 🛟 Troubleshooting

### Common Issues

**"Failed to initialize Pyodide"**
- Check internet connection
- Try refreshing the page
- Ensure browser supports WebAssembly

**"CORS error when accessing URL"**
- Repository may block browser requests
- Try using a CORS proxy service
- Some URLs work better than others

**"Out of memory" errors**
- Reduce download size limit
- Try smaller datasets
- Close other browser tabs
- Use desktop browser instead of mobile

**Map not loading**
- Check browser console for errors
- Ensure JavaScript is enabled
- Try refreshing the page

### Performance Tips

1. **Reduce Download Size**: Set smaller limits in advanced options
2. **Use Sample Files**: Start with smaller test datasets
3. **Close Other Tabs**: Free up browser memory
4. **Use Desktop Browser**: Better performance than mobile
5. **Stable Connection**: Ensure reliable internet for package downloads

## 📊 Browser Testing Results

Tested across different browsers for compatibility:

- ✅ **Chrome 118+**: Full functionality, best performance
- ✅ **Firefox 118+**: Good functionality, slight performance impact
- ✅ **Safari 16+**: Works well, may need memory management
- ✅ **Edge 118+**: Good compatibility and performance
- ⚠️ **Mobile Browsers**: Limited by device memory

## 🤝 Contributing

To contribute to the web version:

1. **Fork** the repository
2. **Create** a feature branch
3. **Test** in multiple browsers
4. **Submit** a pull request

### Development Guidelines

- **Responsive Design**: Ensure mobile compatibility
- **Accessibility**: Follow WCAG guidelines
- **Performance**: Optimize for slower devices
- **Documentation**: Update this README for changes

## 📜 License

Same as the main geoextent project: MIT License

## 🔗 Links

- **Main Project**: [github.com/nuest/geoextent](https://github.com/nuest/geoextent)
- **Pyodide**: [pyodide.org](https://pyodide.org/)
- **Leaflet**: [leafletjs.com](https://leafletjs.com/)
- **Bootstrap**: [getbootstrap.com](https://getbootstrap.com/)

---

*Built with ❤️ using Pyodide, Leaflet, and modern web technologies*