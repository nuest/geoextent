/**
 * Main Application Logic for Geoextent Web
 * Handles user interactions, form validation, and coordinates between Pyodide and Leaflet
 */

class GeoextentApp {
    constructor() {
        this.mapHandler = new MapHandler();
        this.initialized = false;
        this.processing = false;

        // UI elements
        this.elements = {
            initStatus: document.getElementById('init-status'),
            initMessage: document.getElementById('init-message'),
            initProgress: document.getElementById('init-progress'),
            form: document.getElementById('geoextent-form'),
            urlInput: document.getElementById('url-input'),
            extractBtn: document.getElementById('extract-btn'),
            processingStatus: document.getElementById('processing-status'),
            processingMessage: document.getElementById('processing-message'),
            resultsSection: document.getElementById('results-section'),
            resultsContent: document.getElementById('results-content'),
            errorSection: document.getElementById('error-section'),
            errorContent: document.getElementById('error-content'),
            copyBtn: document.getElementById('copy-results-btn')
        };

        // Form option elements
        this.options = {
            bbox: document.getElementById('bbox-toggle'),
            tbox: document.getElementById('tbox-toggle'),
            format: document.getElementById('format-select'),
            maxDownloadSize: document.getElementById('max-download-size'),
            downloadMethod: document.getElementById('download-method'),
            timeout: document.getElementById('timeout')
        };

        this.lastResult = null;
    }

    /**
     * Initialize the application
     */
    async initialize() {
        try {
            // Initialize map
            this.mapHandler.initialize();

            // Set up event listeners
            this.setupEventListeners();

            // Initialize Pyodide
            await this.initializePyodide();

            this.initialized = true;

        } catch (error) {
            console.error('Failed to initialize application:', error);
            this.showError('Failed to initialize the application. Please refresh the page.');
        }
    }

    /**
     * Set up all event listeners
     */
    setupEventListeners() {
        // Form submission
        this.elements.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleExtraction();
        });

        // Copy results button
        this.elements.copyBtn.addEventListener('click', () => {
            this.copyResults();
        });

        // URL input validation
        this.elements.urlInput.addEventListener('input', () => {
            this.validateInput();
        });

        // Map resize on window resize
        window.addEventListener('resize', () => {
            this.mapHandler.resize();
        });

        // Bootstrap accordion events for responsive design
        document.querySelectorAll('.accordion-button').forEach(button => {
            button.addEventListener('click', () => {
                setTimeout(() => this.mapHandler.resize(), 150);
            });
        });
    }

    /**
     * Initialize Pyodide and geoextent
     */
    async initializePyodide() {
        try {
            await window.geoextentWasm.initialize((message) => {
                this.updateInitProgress(message);
            });

            // Test that geoextent is properly loaded
            try {
                const testResult = window.geoextentWasm.pyodide.runPython(`
# Test GDAL first as it's critical
try:
    from osgeo import gdal, ogr, osr
    gdal_result = f"GDAL OK (v{gdal.__version__})"
except Exception as e:
    result = f"CRITICAL: GDAL/osgeo failed: {str(e)}"

if 'CRITICAL' not in locals().get('result', ''):
    try:
        import geoextent
        result = f"{gdal_result}, basic geoextent import successful"

        try:
            import geoextent.lib.content_providers
            result += ", content_providers imported"
        except Exception as e:
            result += f", content_providers failed: {str(e)}"

        try:
            import geoextent.lib.extent as extent
            result += ", extent imported"
        except Exception as e:
            result += f", extent failed: {str(e)}"

        try:
            import geoextent.lib.helpfunctions
            result += ", helpfunctions imported"
        except Exception as e:
            result += f", helpfunctions failed: {str(e)}"

        if "failed" not in result:
            result = "Geoextent loaded successfully with all modules"
    except Exception as e:
        result = f"Geoextent loading failed: {str(e)}"

result
`);
                console.log('Geoextent test result:', testResult);

                if (testResult.includes('failed')) {
                    throw new Error(testResult);
                }
            } catch (testError) {
                console.error('Geoextent test failed:', testError);
                throw new Error('Geoextent modules not properly loaded');
            }

            // Enable the form
            this.elements.urlInput.disabled = false;
            this.elements.extractBtn.disabled = false;

            // Hide initialization status
            this.elements.initStatus.style.display = 'none';

            console.log('Pyodide and geoextent initialized successfully');

        } catch (error) {
            this.updateInitProgress('Failed to initialize: ' + error.message);
            console.error('Initialization error:', error);
            throw error;
        }
    }

    /**
     * Update initialization progress
     */
    updateInitProgress(message) {
        this.elements.initMessage.textContent = message;

        // Update progress bar (simple progression)
        const progress = this.elements.initProgress;
        if (message.includes('Loading Pyodide')) {
            progress.style.width = '20%';
        } else if (message.includes('Loading GDAL')) {
            progress.style.width = '40%';
        } else if (message.includes('Installing packages') || message.includes('additional geospatial')) {
            progress.style.width = '60%';
        } else if (message.includes('Loading geoextent')) {
            progress.style.width = '80%';
        } else if (message.includes('Ready')) {
            progress.style.width = '100%';
            setTimeout(() => {
                this.elements.initStatus.classList.remove('alert-info');
                this.elements.initStatus.classList.add('alert-success');
                this.elements.initMessage.innerHTML = '<i class="fas fa-check me-2"></i>Ready to extract extents!';
            }, 500);
        } else if (message.includes('Error')) {
            progress.style.width = '100%';
            this.elements.initStatus.classList.remove('alert-info');
            this.elements.initStatus.classList.add('alert-danger');
            this.elements.initMessage.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>' + message;
        }
    }

    /**
     * Validate URL input
     */
    validateInput() {
        const url = this.elements.urlInput.value.trim();
        const isValid = this.isValidUrl(url) || this.isValidDoi(url);

        if (url && !isValid) {
            this.elements.urlInput.classList.add('is-invalid');
            this.elements.extractBtn.disabled = true;
        } else {
            this.elements.urlInput.classList.remove('is-invalid');
            this.elements.extractBtn.disabled = !url || !this.initialized;
        }

        return isValid;
    }

    /**
     * Check if URL is valid
     */
    isValidUrl(string) {
        try {
            const url = new URL(string);
            return url.protocol === 'http:' || url.protocol === 'https:';
        } catch (_) {
            return false;
        }
    }

    /**
     * Check if DOI is valid
     */
    isValidDoi(string) {
        const doiPattern = /^(doi:)?(10\.\d{4,}\/[^\s]+)$/i;
        return doiPattern.test(string);
    }

    /**
     * Handle extent extraction
     */
    async handleExtraction() {
        if (this.processing) {
            return;
        }

        try {
            this.processing = true;
            this.showProcessing('Starting extraction...');
            this.hideResults();
            this.hideError();

            // Validate input
            if (!this.validateInput()) {
                throw new Error('Please enter a valid URL or DOI');
            }

            // Get form values
            const url = this.elements.urlInput.value.trim();
            const options = this.getExtractionOptions();

            this.showProcessing('Extracting geospatial extent...');

            // Call geoextent
            const result = await window.geoextentWasm.extractExtent(url, options);

            if (result.error) {
                throw new Error(result.error);
            }

            // Display results
            this.displayResults(result);

            // Update map
            if (result.bbox) {
                this.mapHandler.displayExtent(result, {
                    clearPrevious: true,
                    fitBounds: true
                });
            }

            this.hideProcessing();

        } catch (error) {
            console.error('Extraction failed:', error);
            this.showError(error.message);
            this.hideProcessing();
        } finally {
            this.processing = false;
        }
    }

    /**
     * Get extraction options from form
     */
    getExtractionOptions() {
        return {
            bbox: this.options.bbox.checked,
            tbox: this.options.tbox.checked,
            format: this.options.format.value,
            max_download_size: this.options.maxDownloadSize.value || null,
            max_download_method: this.options.downloadMethod.value,
            timeout: parseInt(this.options.timeout.value) * 1000 // Convert to milliseconds
        };
    }

    /**
     * Display extraction results
     */
    displayResults(result) {
        this.lastResult = result;

        // Format result for display
        const formattedResult = JSON.stringify(result, null, 2);
        this.elements.resultsContent.innerHTML = `<pre>${formattedResult}</pre>`;

        // Show results section
        this.elements.resultsSection.style.display = 'block';
        this.elements.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    /**
     * Copy results to clipboard
     */
    async copyResults() {
        if (!this.lastResult) return;

        try {
            const text = JSON.stringify(this.lastResult, null, 2);
            await navigator.clipboard.writeText(text);

            // Show feedback
            const originalText = this.elements.copyBtn.innerHTML;
            this.elements.copyBtn.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
            this.elements.copyBtn.classList.add('btn-copied');

            setTimeout(() => {
                this.elements.copyBtn.innerHTML = originalText;
                this.elements.copyBtn.classList.remove('btn-copied');
            }, 2000);

        } catch (error) {
            console.error('Failed to copy:', error);
            this.showError('Failed to copy results to clipboard');
        }
    }

    /**
     * Show processing status
     */
    showProcessing(message) {
        this.elements.processingMessage.textContent = message;
        this.elements.processingStatus.style.display = 'block';
        this.elements.extractBtn.disabled = true;
    }

    /**
     * Hide processing status
     */
    hideProcessing() {
        this.elements.processingStatus.style.display = 'none';
        this.elements.extractBtn.disabled = false;
    }

    /**
     * Show results section
     */
    showResults() {
        this.elements.resultsSection.style.display = 'block';
    }

    /**
     * Hide results section
     */
    hideResults() {
        this.elements.resultsSection.style.display = 'none';
    }

    /**
     * Show error message
     */
    showError(message) {
        this.elements.errorContent.innerHTML = `
            <p class="mb-0">${message}</p>
            <details class="mt-2">
                <summary class="cursor-pointer">Troubleshooting Tips</summary>
                <ul class="mt-2 mb-0 small">
                    <li>Ensure the URL is accessible and points to a valid repository</li>
                    <li>Check that the repository contains geospatial data files</li>
                    <li>Some repositories may have access restrictions</li>
                    <li>Try reducing the timeout or download size limit</li>
                    <li>CORS restrictions may prevent access to some domains</li>
                    <li><strong>WASM limitations:</strong> PANGAEA support not available (requires pangaeapy), archive extraction limited (patool dependency)</li>
                </ul>
            </details>
        `;
        this.elements.errorSection.style.display = 'block';
        this.elements.errorSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    /**
     * Hide error section
     */
    hideError() {
        this.elements.errorSection.style.display = 'none';
    }

    /**
     * Add sample URLs for testing
     */
    addSampleUrls() {
        const samples = [
            'https://zenodo.org/record/4281387',
            'https://doi.org/10.5281/zenodo.4281387',
            'https://figshare.com/articles/dataset/Example_Dataset/12345678',
            'https://datadryad.org/stash/dataset/doi:10.5061/dryad.example'
        ];

        const sampleContainer = document.createElement('div');
        sampleContainer.className = 'mt-2';
        sampleContainer.innerHTML = `
            <label class="form-label small text-muted">Sample URLs:</label>
            <div class="d-flex flex-wrap gap-1">
                ${samples.map(url => `
                    <button type="button" class="btn btn-outline-secondary btn-sm sample-url-btn"
                            data-url="${url}" title="Click to use this sample URL">
                        ${this.truncateUrl(url)}
                    </button>
                `).join('')}
            </div>
        `;

        // Insert after URL input
        this.elements.urlInput.parentNode.appendChild(sampleContainer);

        // Add click handlers
        sampleContainer.querySelectorAll('.sample-url-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.elements.urlInput.value = btn.dataset.url;
                this.validateInput();
            });
        });
    }

    /**
     * Truncate URL for display
     */
    truncateUrl(url) {
        const maxLength = 25;
        if (url.length <= maxLength) return url;

        const start = url.substring(0, 12);
        const end = url.substring(url.length - 10);
        return `${start}...${end}`;
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    const app = new GeoextentApp();

    try {
        await app.initialize();
        console.log('Geoextent Web application initialized successfully');

        // Add sample URLs for testing
        app.addSampleUrls();

    } catch (error) {
        console.error('Failed to initialize Geoextent Web:', error);
    }
});

// Export for debugging
window.GeoextentApp = GeoextentApp;