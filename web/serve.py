#!/usr/bin/env python3
"""
Simple HTTP server for testing the Geoextent Web application locally.

This server serves the web application with appropriate CORS headers
and MIME types for WebAssembly and other assets.
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS support and proper MIME types."""

    def end_headers(self):
        """Add CORS headers to all responses."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        super().end_headers()

    def guess_type(self, path):
        """Override to handle additional MIME types."""
        # Handle WebAssembly files first
        if path.endswith('.wasm'):
            return 'application/wasm'
        elif path.endswith('.js'):
            return 'application/javascript'
        elif path.endswith('.mjs'):
            return 'application/javascript'
        elif path.endswith('.json'):
            return 'application/json'
        # Handle font files
        elif path.endswith('.woff2'):
            return 'font/woff2'
        elif path.endswith('.woff'):
            return 'font/woff'
        elif path.endswith('.ttf'):
            return 'font/ttf'
        elif path.endswith('.eot'):
            return 'application/vnd.ms-fontobject'
        elif path.endswith('.otf'):
            return 'font/otf'

        # For other files, use the parent method
        try:
            result = super().guess_type(path)
            if isinstance(result, tuple) and len(result) >= 2:
                return result[0]  # Return just the mimetype
            return result
        except Exception:
            return 'application/octet-stream'  # Default fallback

    def do_OPTIONS(self):
        """Handle preflight OPTIONS requests."""
        self.send_response(200)
        self.end_headers()

def main():
    """Start the development server."""
    # Change to the web directory
    web_dir = Path(__file__).parent
    os.chdir(web_dir)

    # Configuration
    PORT = 8088
    HOST = 'localhost'

    # Create server
    with socketserver.TCPServer((HOST, PORT), CORSHTTPRequestHandler) as httpd:
        print(f"\\n🌐 Geoextent Web Development Server")
        print(f"📁 Serving directory: {web_dir}")
        print(f"🔗 Local URL: http://{HOST}:{PORT}")
        print(f"📱 Network URL: http://{get_local_ip()}:{PORT}")
        print(f"\\n⚡ Server running on port {PORT}")
        print("🛑 Press Ctrl+C to stop the server\\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\\n🛑 Server stopped.")

def get_local_ip():
    """Get the local IP address for network access."""
    import socket
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "localhost"

if __name__ == "__main__":
    main()