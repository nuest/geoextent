/**
 * Map Handler for Geoextent Web
 * Manages Leaflet map interactions and extent visualization
 */

class MapHandler {
    constructor(mapContainerId = 'map') {
        this.mapContainerId = mapContainerId;
        this.map = null;
        this.currentLayer = null;
        this.extentLayers = [];
        this.initialized = false;
    }

    /**
     * Initialize the Leaflet map
     */
    initialize() {
        if (this.initialized) return;

        try {
            // Initialize map with default view
            this.map = L.map(this.mapContainerId).setView([20, 0], 2);

            // Add OpenStreetMap tile layer with fallback
            let tileLayer;
            let tileErrorCount = 0;

            const addTileLayer = (url, attribution, id) => {
                const layer = L.tileLayer(url, {
                    attribution: attribution,
                    maxZoom: 18,
                    subdomains: ['a', 'b', 'c'],
                    id: id,
                    crossOrigin: 'anonymous'
                });

                layer.on('tileerror', (error) => {
                    tileErrorCount++;
                    console.warn(`Tile loading error (${id}):`, error);

                    // If too many errors with OSM, try fallback
                    if (tileErrorCount > 5 && id === 'osm' && !this.map.hasLayer(fallbackLayer)) {
                        console.log('Switching to fallback tile server');
                        this.map.removeLayer(layer);
                        fallbackLayer.addTo(this.map);
                    }
                });

                return layer;
            };

            // Primary tile layer (OpenStreetMap)
            tileLayer = addTileLayer(
                'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                'osm'
            );

            // Fallback tile layer (CartoDB)
            const fallbackLayer = addTileLayer(
                'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
                '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, © <a href="https://carto.com/attributions">CARTO</a>',
                'cartodb'
            );

            // Add primary layer to map
            tileLayer.addTo(this.map);

            // Add scale control
            L.control.scale({
                position: 'bottomright',
                metric: true,
                imperial: true
            }).addTo(this.map);

            // Custom control for layer management
            this.addLayerControl();

            this.initialized = true;
            console.log('Map initialized successfully');

        } catch (error) {
            console.error('Failed to initialize map:', error);
            this.showMapError('Failed to initialize map. Please refresh the page.');
        }
    }

    /**
     * Add custom layer control for managing extent layers
     */
    addLayerControl() {
        const LayerControl = L.Control.extend({
            onAdd: function(map) {
                const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
                container.innerHTML = `
                    <a href="#" title="Clear all extents" style="
                        background: white;
                        color: #333;
                        display: block;
                        text-decoration: none;
                        line-height: 30px;
                        text-align: center;
                        font-size: 14px;
                        padding: 0 8px;
                    ">
                        <i class="fas fa-trash"></i>
                    </a>
                `;

                container.onclick = (e) => {
                    e.preventDefault();
                    this.clearAllExtents();
                };

                return container;
            }.bind(this)
        });

        new LayerControl({ position: 'topright' }).addTo(this.map);
    }

    /**
     * Display extent on the map
     * @param {Object} extentData - The extent data from geoextent
     * @param {Object} options - Display options
     */
    displayExtent(extentData, options = {}) {
        if (!this.initialized) {
            console.warn('Map not initialized');
            return;
        }

        try {
            // Clear previous extent if options.clearPrevious is true
            if (options.clearPrevious) {
                this.clearAllExtents();
            }

            let layer = null;
            const defaultStyle = {
                color: '#007bff',
                weight: 3,
                opacity: 0.8,
                fillColor: '#007bff',
                fillOpacity: 0.2
            };

            const style = { ...defaultStyle, ...options.style };

            if (extentData.bbox) {
                if (typeof extentData.bbox === 'string') {
                    // Handle WKT format
                    layer = this.addWKTExtent(extentData.bbox, style, options);
                } else if (extentData.bbox.type === 'FeatureCollection') {
                    // Handle GeoJSON format
                    layer = this.addGeoJSONExtent(extentData.bbox, style, options);
                } else if (Array.isArray(extentData.bbox) && extentData.bbox.length === 4) {
                    // Handle bounding box array [minX, minY, maxX, maxY]
                    layer = this.addBBoxExtent(extentData.bbox, style, options);
                }
            }

            if (layer) {
                this.extentLayers.push(layer);

                // Add popup with extent information
                const popupContent = this.createExtentPopup(extentData);
                layer.bindPopup(popupContent);

                // Fit map to extent if requested
                if (options.fitBounds !== false) {
                    this.map.fitBounds(layer.getBounds(), {
                        padding: [20, 20],
                        maxZoom: 10
                    });
                }

                return layer;
            }

        } catch (error) {
            console.error('Error displaying extent:', error);
            this.showMapError('Failed to display extent on map');
        }

        return null;
    }

    /**
     * Add WKT extent to map
     */
    addWKTExtent(wktString, style, options) {
        try {
            // Parse WKT POLYGON format
            const coordsMatch = wktString.match(/POLYGON\s*\(\s*\(\s*([^)]+)\s*\)\s*\)/i);
            if (!coordsMatch) {
                throw new Error('Invalid WKT format');
            }

            const coordsString = coordsMatch[1];
            const coords = coordsString.split(',').map(pair => {
                const [x, y] = pair.trim().split(/\s+/).map(Number);
                return [y, x]; // Leaflet uses [lat, lng] format
            });

            // Remove the last coordinate if it's the same as the first (closing the polygon)
            if (coords.length > 1 &&
                coords[0][0] === coords[coords.length - 1][0] &&
                coords[0][1] === coords[coords.length - 1][1]) {
                coords.pop();
            }

            const polygon = L.polygon(coords, style);
            polygon.addTo(this.map);

            return polygon;

        } catch (error) {
            console.error('Error parsing WKT:', error);
            throw new Error('Failed to parse WKT geometry');
        }
    }

    /**
     * Add GeoJSON extent to map
     */
    addGeoJSONExtent(geoJsonData, style, options) {
        try {
            const layer = L.geoJSON(geoJsonData, {
                style: style,
                onEachFeature: (feature, layer) => {
                    if (feature.properties && feature.properties.description) {
                        layer.bindTooltip(feature.properties.description);
                    }
                }
            });

            layer.addTo(this.map);
            return layer;

        } catch (error) {
            console.error('Error adding GeoJSON:', error);
            throw new Error('Failed to add GeoJSON to map');
        }
    }

    /**
     * Add bounding box extent to map
     */
    addBBoxExtent(bbox, style, options) {
        try {
            const [minX, minY, maxX, maxY] = bbox;

            // Create rectangle bounds
            const bounds = [[minY, minX], [maxY, maxX]];
            const rectangle = L.rectangle(bounds, style);
            rectangle.addTo(this.map);

            return rectangle;

        } catch (error) {
            console.error('Error adding bounding box:', error);
            throw new Error('Failed to add bounding box to map');
        }
    }

    /**
     * Create popup content for extent information
     */
    createExtentPopup(extentData) {
        let content = '<div class="extent-popup"><h6><i class="fas fa-info-circle me-2"></i>Extent Information</h6>';

        // Spatial extent
        if (extentData.bbox) {
            content += '<p><strong>Spatial Extent:</strong></p>';

            if (typeof extentData.bbox === 'string') {
                content += `<code style="font-size: 11px; word-break: break-all;">${extentData.bbox}</code>`;
            } else if (Array.isArray(extentData.bbox)) {
                const [minX, minY, maxX, maxY] = extentData.bbox;
                content += `
                    <small>
                        Min: ${minX.toFixed(4)}, ${minY.toFixed(4)}<br>
                        Max: ${maxX.toFixed(4)}, ${maxY.toFixed(4)}
                    </small>
                `;
            }
        }

        // Temporal extent
        if (extentData.tbox) {
            content += '<p class="mt-2"><strong>Temporal Extent:</strong></p>';
            if (extentData.tbox.begin && extentData.tbox.end) {
                content += `<small>${extentData.tbox.begin} to ${extentData.tbox.end}</small>`;
            } else {
                content += '<small>Available (see JSON output)</small>';
            }
        }

        // Format information
        if (extentData.format) {
            content += `<p class="mt-2"><small><strong>Format:</strong> ${extentData.format}</small></p>`;
        }

        content += '</div>';
        return content;
    }

    /**
     * Clear all extent layers from the map
     */
    clearAllExtents() {
        this.extentLayers.forEach(layer => {
            if (this.map.hasLayer(layer)) {
                this.map.removeLayer(layer);
            }
        });
        this.extentLayers = [];
        console.log('Cleared all extent layers');
    }

    /**
     * Resize map (useful when container size changes)
     */
    resize() {
        if (this.map) {
            setTimeout(() => {
                this.map.invalidateSize();
            }, 100);
        }
    }

    /**
     * Show error message on map
     */
    showMapError(message) {
        if (!this.map) return;

        const errorControl = L.control({ position: 'topleft' });
        errorControl.onAdd = function() {
            const div = L.DomUtil.create('div', 'alert alert-danger map-error');
            div.innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
                <button type="button" class="btn-close btn-close-white float-end" onclick="this.parentElement.remove()"></button>
            `;
            return div;
        };

        errorControl.addTo(this.map);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (this.map.hasControl(errorControl)) {
                this.map.removeControl(errorControl);
            }
        }, 5000);
    }

    /**
     * Add marker at specific coordinates
     */
    addMarker(lat, lng, options = {}) {
        if (!this.map) return null;

        const marker = L.marker([lat, lng], options);
        marker.addTo(this.map);

        if (options.popup) {
            marker.bindPopup(options.popup);
        }

        return marker;
    }

    /**
     * Get current map bounds
     */
    getBounds() {
        return this.map ? this.map.getBounds() : null;
    }

    /**
     * Set map view to specific coordinates and zoom
     */
    setView(lat, lng, zoom = 5) {
        if (this.map) {
            this.map.setView([lat, lng], zoom);
        }
    }

    /**
     * Export current map view as image (if supported)
     */
    async exportImage() {
        // This would require additional libraries like leaflet-image
        // For now, we'll just show a message
        console.log('Image export not implemented yet');
        return null;
    }
}

// Export for use in other modules
window.MapHandler = MapHandler;