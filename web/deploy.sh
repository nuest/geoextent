#!/bin/bash

# Deployment script for Geoextent Web
# This script prepares the web application for production deployment

set -e

echo "🚀 Geoextent Web Deployment Script"
echo "=================================="

# Check if we're in the correct directory
if [[ ! -f "index.html" ]]; then
    echo "❌ Error: This script must be run from the web/ directory"
    exit 1
fi

# Create deployment directory
DEPLOY_DIR="dist"
echo "📁 Creating deployment directory: $DEPLOY_DIR"
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

# Copy essential files
echo "📄 Copying application files..."
cp index.html "$DEPLOY_DIR/"
cp -r assets/ "$DEPLOY_DIR/"

# Build the geoextent package
echo "🔧 Building geoextent package..."
python build.py

# Copy build output
echo "📦 Copying build output..."
cp -r build/ "$DEPLOY_DIR/"

# Copy documentation
echo "📚 Copying documentation..."
cp README.md "$DEPLOY_DIR/"
cp TESTING.md "$DEPLOY_DIR/"

# Create a simple index for documentation
cat > "$DEPLOY_DIR/docs.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Geoextent Web - Documentation</title>
    <link href="assets/lib/bootstrap/bootstrap.min.css" rel="stylesheet">
</head>
<body class="container py-4">
    <h1>📚 Geoextent Web Documentation</h1>
    <div class="row">
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">User Guide</h5>
                    <p class="card-text">Complete guide for using Geoextent Web</p>
                    <a href="README.md" class="btn btn-primary">View README</a>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">Testing Guide</h5>
                    <p class="card-text">Browser testing checklist and procedures</p>
                    <a href="TESTING.md" class="btn btn-primary">View Testing Guide</a>
                </div>
            </div>
        </div>
    </div>
    <div class="mt-4">
        <a href="index.html" class="btn btn-success">← Back to Application</a>
    </div>
</body>
</html>
EOF

# Optimize assets (optional - requires tools)
echo "🎯 Optimizing assets..."

# Check if we can minify CSS
if command -v cssnano &> /dev/null; then
    echo "   Minifying CSS files..."
    find "$DEPLOY_DIR/assets/css" -name "*.css" -exec cssnano {} {}.min \;
else
    echo "   CSS minification skipped (cssnano not found)"
fi

# Check if we can minify JS
if command -v terser &> /dev/null; then
    echo "   Minifying JavaScript files..."
    find "$DEPLOY_DIR/assets/js" -name "*.js" -exec terser {} -o {}.min \;
else
    echo "   JavaScript minification skipped (terser not found)"
fi

# Create .htaccess for Apache servers
cat > "$DEPLOY_DIR/.htaccess" << EOF
# Geoextent Web - Apache Configuration

# Enable CORS for all origins (adjust for production)
Header always set Access-Control-Allow-Origin "*"
Header always set Access-Control-Allow-Methods "GET, POST, OPTIONS"
Header always set Access-Control-Allow-Headers "Content-Type"

# Required headers for SharedArrayBuffer (needed by Pyodide)
Header always set Cross-Origin-Embedder-Policy "require-corp"
Header always set Cross-Origin-Opener-Policy "same-origin"

# MIME types for WebAssembly
AddType application/wasm .wasm

# Cache control for better performance
<filesMatch "\\.(css|js|wasm|woff2?)$">
    Header set Cache-Control "max-age=31536000, public"
</filesMatch>

# Security headers
Header always set X-Content-Type-Options "nosniff"
Header always set X-Frame-Options "SAMEORIGIN"
Header always set X-XSS-Protection "1; mode=block"

# Compression
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/plain
    AddOutputFilterByType DEFLATE text/html
    AddOutputFilterByType DEFLATE text/xml
    AddOutputFilterByType DEFLATE text/css
    AddOutputFilterByType DEFLATE application/xml
    AddOutputFilterByType DEFLATE application/xhtml+xml
    AddOutputFilterByType DEFLATE application/rss+xml
    AddOutputFilterByType DEFLATE application/javascript
    AddOutputFilterByType DEFLATE application/x-javascript
</IfModule>
EOF

# Create nginx configuration
cat > "$DEPLOY_DIR/nginx.conf" << EOF
# Geoextent Web - Nginx Configuration
# Include this in your nginx server block

location / {
    try_files \$uri \$uri/ /index.html;

    # CORS headers
    add_header Access-Control-Allow-Origin "*" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type" always;

    # Required headers for SharedArrayBuffer
    add_header Cross-Origin-Embedder-Policy "require-corp" always;
    add_header Cross-Origin-Opener-Policy "same-origin" always;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
}

# WebAssembly MIME type
location ~* \.wasm$ {
    add_header Content-Type "application/wasm";
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Cache static assets
location ~* \.(css|js|woff2?)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
EOF

# Create deployment info file
cat > "$DEPLOY_DIR/deployment-info.json" << EOF
{
    "name": "Geoextent Web",
    "version": "1.0.0",
    "build_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "build_host": "$(hostname)",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')",
    "dependencies": {
        "pyodide": "0.24.1",
        "leaflet": "1.9.4",
        "bootstrap": "5.3.2",
        "font_awesome": "6.4.0"
    },
    "features": [
        "Repository URL processing",
        "Interactive maps",
        "Multiple output formats",
        "Responsive design",
        "Download size limiting",
        "Temporal extent extraction"
    ]
}
EOF

# Calculate sizes
TOTAL_SIZE=$(du -sh "$DEPLOY_DIR" | cut -f1)
FILE_COUNT=$(find "$DEPLOY_DIR" -type f | wc -l)

echo ""
echo "✅ Deployment completed successfully!"
echo "📊 Statistics:"
echo "   📁 Total size: $TOTAL_SIZE"
echo "   📄 File count: $FILE_COUNT"
echo "   📂 Output directory: $DEPLOY_DIR"
echo ""
echo "🚀 Deployment options:"
echo "   1. Static hosting: Upload $DEPLOY_DIR contents to your web server"
echo "   2. GitHub Pages: Push $DEPLOY_DIR to gh-pages branch"
echo "   3. Netlify: Drag & drop $DEPLOY_DIR folder to Netlify"
echo "   4. Vercel: Run 'vercel --prod' in $DEPLOY_DIR"
echo ""
echo "⚠️  Important:"
echo "   - Ensure CORS headers are configured on your server"
echo "   - WebAssembly requires HTTPS for some features"
echo "   - Test in multiple browsers after deployment"
echo ""
echo "📖 For more information, see README.md and TESTING.md"
EOF

# Make the script executable
chmod +x deploy.sh