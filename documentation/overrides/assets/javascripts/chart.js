// noinspection JSUnresolvedReference

/**
 * ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
 * ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
 * ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
 * ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
 * ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
 * ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
 * Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
 */

// Chart.js is loaded from vendor/chart.min.js via main.html
// See tools/vendor-builder for vendor management

/**
 * @typedef {Object} Chart
 * @property {Object} defaults - Chart.js global defaults
 */

/* global Chart */

// Initialize Phantom modules namespace
window.PhantomModules = window.PhantomModules || {};

// Define initialization function for lazy loading
window.PhantomModules.initChart = function() {
    // Get Chart from window (it's loaded dynamically)
    /** @type {any} */
    const Chart = window.Chart;
    
    // Check if Chart.js is available
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded');
        return;
    }

    // Configure Chart.js defaults for theme compatibility
    updateChartDefaults();

    // Initialize all charts
    initializeCharts();
    
    // Setup theme observer
    setupThemeObserver();
};

// Also support traditional loading (backward compatibility)
document.addEventListener('DOMContentLoaded', function() {
    // If Chart.js is already loaded (non-lazy loading), initialize immediately
    if (typeof window.Chart !== 'undefined' && !window.PhantomModules.chartInitialized) {
        window.PhantomModules.chartInitialized = true;
        window.PhantomModules.initChart();
    }
});

function initializeCharts() {
    // Find all chart containers
    const chartContainers = document.querySelectorAll('.chart-container');
    
    chartContainers.forEach((container) => {
        // Skip if already has a chart
        if (container.chartInstance) {
            return;
        }
        
        // Check for JSON config attribute
        const configAttr = container.getAttribute('data-chart-config');
        const titleAttr = container.getAttribute('data-chart-title');
        const variableAttr = container.getAttribute('data-chart-variable');
        
        if (configAttr) {
            try {
                const config = JSON.parse(configAttr);
                if (titleAttr) {
                    config.title = titleAttr;
                }
                renderChart(container, config);
            } catch (e) {
                console.error('Error parsing chart config:', e);
            }
        } else if (variableAttr) {
            // Support for legacy data-chart-variable format
            try {
                // Try to get the variable from global scope
                const config = window[variableAttr];
                if (config) {
                    renderChart(container, config);
                } else {
                    console.warn('Chart variable not found:', variableAttr);
                }
            } catch (e) {
                console.error('Error loading chart variable:', e);
            }
        }
    });
}

/**
 * Render individual chart
 * @param {HTMLElement} container - The container element
 * @param {Object} config - Chart configuration object
 */
function renderChart(container, config) {
    // Clear container
    container.innerHTML = '';
    
    // Set container to relative positioning
    container.style.position = 'relative';
    
    // Add title if specified
    if (config.title) {
        const title = document.createElement('h4');
        title.className = 'chart-title';
        title.textContent = config.title;
        container.appendChild(title);
    }
    
    // Create wrapper div for canvas
    const canvasWrapper = document.createElement('div');
    canvasWrapper.style.position = 'relative';
    canvasWrapper.style.flex = '1';
    canvasWrapper.style.minHeight = '0';
    canvasWrapper.style.overflow = 'hidden';
    container.appendChild(canvasWrapper);
    
    // Create canvas element
    const canvas = document.createElement('canvas');
    canvasWrapper.appendChild(canvas);
    
    // Add rotate indicator for mobile
    const rotateIndicator = createRotateIndicator();
    container.appendChild(rotateIndicator);
    
    // Get the 2D context
    const ctx = canvas.getContext('2d');
    
    // Apply theme-aware styling
    const themedConfig = applyThemeToConfig(config);
    
    // Create the chart (Chart is available globally)
    // noinspection JSUnresolvedFunction
    const ChartConstructor = /** @type {any} */ (window.Chart);
    container.chartInstance = new ChartConstructor(ctx, themedConfig);
}

/**
 * Create rotate phone indicator element
 * @returns {HTMLElement} The rotate indicator element
 */
function createRotateIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'chart-rotate-indicator';
    
    // Create SVG icon
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'chart-rotate-icon');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'currentColor');
    
    // Phone path
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M7 1.5C7 0.67 7.67 0 8.5 0h7c.83 0 1.5.67 1.5 1.5v21c0 .83-.67 1.5-1.5 1.5h-7C7.67 24 7 23.33 7 22.5v-21zM9 3v16h6V3H9zm3 18.5c.55 0 1-.45 1-1s-.45-1-1-1-1 .45-1 1 .45 1 1 1z');
    svg.appendChild(path);
    
    // Create message
    const message = document.createElement('p');
    message.className = 'rotate-message';
    message.textContent = 'Rotate your device for better view';
    
    // Append elements
    indicator.appendChild(svg);
    indicator.appendChild(message);
    
    return indicator;
}

// Apply theme-aware styling to chart config
function applyThemeToConfig(config) {
    const themedConfig = JSON.parse(JSON.stringify(config)); // Deep clone
    
    // Get current theme colors
    const isDarkMode = document.body.getAttribute('data-md-color-scheme') === 'slate';
    const textColor = isDarkMode ? '#ffffff' : '#000000';
    const gridColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    
    // Apply theme colors to chart options
    if (!themedConfig.options) themedConfig.options = {};
    if (!themedConfig.options.plugins) themedConfig.options.plugins = {};
    
    // Legend styling
    if (!themedConfig.options.plugins.legend) themedConfig.options.plugins.legend = {};
    if (!themedConfig.options.plugins.legend.labels) themedConfig.options.plugins.legend.labels = {};
    themedConfig.options.plugins.legend.labels.color = textColor;
    themedConfig.options.plugins.legend.labels.font = themedConfig.options.plugins.legend.labels.font || {};
    themedConfig.options.plugins.legend.labels.font.size = 14;
    
    // Tooltip styling
    if (!themedConfig.options.plugins.tooltip) themedConfig.options.plugins.tooltip = {};
    themedConfig.options.plugins.tooltip.titleColor = textColor;
    themedConfig.options.plugins.tooltip.bodyColor = textColor;
    themedConfig.options.plugins.tooltip.backgroundColor = isDarkMode ? 'rgba(0, 0, 0, 0.8)' : 'rgba(255, 255, 255, 0.8)';
    
    // Scale styling
    if (!themedConfig.options.scales) themedConfig.options.scales = {};
    
    // X-axis styling
    if (themedConfig.options.scales.x !== false) {
        if (!themedConfig.options.scales.x) themedConfig.options.scales.x = {};
        if (!themedConfig.options.scales.x.ticks) themedConfig.options.scales.x.ticks = {};
        if (!themedConfig.options.scales.x.grid) themedConfig.options.scales.x.grid = {};
        themedConfig.options.scales.x.ticks.color = textColor;
        themedConfig.options.scales.x.ticks.font = themedConfig.options.scales.x.ticks.font || {};
        themedConfig.options.scales.x.ticks.font.size = 14;
        themedConfig.options.scales.x.grid.color = gridColor;
        // Title font size
        if (themedConfig.options.scales.x.title) {
            if (!themedConfig.options.scales.x.title.font) themedConfig.options.scales.x.title.font = {};
            themedConfig.options.scales.x.title.font.size = 16;
            themedConfig.options.scales.x.title.font.weight = 'bold';
        }
    }
    
    // Y-axis styling
    if (themedConfig.options.scales.y !== false) {
        if (!themedConfig.options.scales.y) themedConfig.options.scales.y = {};
        if (!themedConfig.options.scales.y.ticks) themedConfig.options.scales.y.ticks = {};
        if (!themedConfig.options.scales.y.grid) themedConfig.options.scales.y.grid = {};
        themedConfig.options.scales.y.ticks.color = textColor;
        themedConfig.options.scales.y.ticks.font = themedConfig.options.scales.y.ticks.font || {};
        themedConfig.options.scales.y.ticks.font.size = 14;
        themedConfig.options.scales.y.grid.color = gridColor;
        // Title font size
        if (themedConfig.options.scales.y.title) {
            if (!themedConfig.options.scales.y.title.font) themedConfig.options.scales.y.title.font = {};
            themedConfig.options.scales.y.title.font.size = 16;
            themedConfig.options.scales.y.title.font.weight = 'bold';
        }
    }
    
    // Handle additional Y-axis (y1) if present
    if (themedConfig.options.scales.y1) {
        if (!themedConfig.options.scales.y1.ticks) themedConfig.options.scales.y1.ticks = {};
        if (!themedConfig.options.scales.y1.grid) themedConfig.options.scales.y1.grid = {};
        themedConfig.options.scales.y1.ticks.color = textColor;
        themedConfig.options.scales.y1.ticks.font = themedConfig.options.scales.y1.ticks.font || {};
        themedConfig.options.scales.y1.ticks.font.size = 14;
        themedConfig.options.scales.y1.grid.color = gridColor;
        // Title font size
        if (themedConfig.options.scales.y1.title) {
            if (!themedConfig.options.scales.y1.title.font) themedConfig.options.scales.y1.title.font = {};
            themedConfig.options.scales.y1.title.font.size = 16;
            themedConfig.options.scales.y1.title.font.weight = 'bold';
        }
    }
    
    // Handle additional Y-axis (y2) if present
    if (themedConfig.options.scales.y2) {
        if (!themedConfig.options.scales.y2.ticks) themedConfig.options.scales.y2.ticks = {};
        if (!themedConfig.options.scales.y2.grid) themedConfig.options.scales.y2.grid = {};
        themedConfig.options.scales.y2.ticks.color = textColor;
        themedConfig.options.scales.y2.ticks.font = themedConfig.options.scales.y2.ticks.font || {};
        themedConfig.options.scales.y2.ticks.font.size = 14;
        themedConfig.options.scales.y2.grid.color = gridColor;
        // Title font size
        if (themedConfig.options.scales.y2.title) {
            if (!themedConfig.options.scales.y2.title.font) themedConfig.options.scales.y2.title.font = {};
            themedConfig.options.scales.y2.title.font.size = 16;
            themedConfig.options.scales.y2.title.font.weight = 'bold';
        }
    }
    
    // Handle radial axis (r) for radar and polarArea charts
    if (themedConfig.options.scales.r) {
        if (!themedConfig.options.scales.r.ticks) themedConfig.options.scales.r.ticks = {};
        if (!themedConfig.options.scales.r.grid) themedConfig.options.scales.r.grid = {};
        themedConfig.options.scales.r.ticks.color = textColor;
        themedConfig.options.scales.r.ticks.font = themedConfig.options.scales.r.ticks.font || {};
        themedConfig.options.scales.r.ticks.font.size = 14;
        themedConfig.options.scales.r.grid.color = gridColor;
        themedConfig.options.scales.r.angleLines = themedConfig.options.scales.r.angleLines || {};
        themedConfig.options.scales.r.angleLines.color = gridColor;
        themedConfig.options.scales.r.pointLabels = themedConfig.options.scales.r.pointLabels || {};
        themedConfig.options.scales.r.pointLabels.color = textColor;
        themedConfig.options.scales.r.pointLabels.font = themedConfig.options.scales.r.pointLabels.font || {};
        themedConfig.options.scales.r.pointLabels.font.size = 14;
    }
    
    // Ensure responsive design
    themedConfig.options.responsive = true;
    themedConfig.options.maintainAspectRatio = false;
    themedConfig.options.aspectRatio = 2;
    
    // Disable animations to prevent issues
    themedConfig.options.animation = false;
    themedConfig.options.animations = {
        colors: false,
        x: false,
        y: false
    };
    
    return themedConfig;
}

// Update Chart.js defaults based on current theme
function updateChartDefaults() {
    const isDarkMode = document.body.getAttribute('data-md-color-scheme') === 'slate';
    const textColor = isDarkMode ? '#ffffff' : '#000000';
    const bgColor = isDarkMode ? '#1e1e1e' : '#ffffff';
    
    // Get Chart from window
    /** @type {any} */
    const Chart = window.Chart;
    if (!Chart) return;
    
    Chart.defaults.font.family = 'Roboto, sans-serif';
    Chart.defaults.font.size = 14;
    Chart.defaults.color = textColor;
    Chart.defaults.backgroundColor = bgColor;
}

// Setup theme observer to watch for theme changes
function setupThemeObserver() {
    // Create observer for theme changes
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'data-md-color-scheme') {
                console.log('Theme changed, updating charts...');
                updateCharts();
            }
        });
    });
    
    // Observe body for attribute changes
    observer.observe(document.body, {
        attributes: true,
        attributeFilter: ['data-md-color-scheme']
    });
    
    // Also listen for the custom theme change event
    document.addEventListener('theme-changed', function() {
        console.log('Theme change event detected');
        updateCharts();
    });
}

// Update all charts when theme changes
function updateCharts() {
    // Update defaults first
    updateChartDefaults();
    
    // Find all chart containers
    const chartContainers = document.querySelectorAll('.chart-container');
    
    chartContainers.forEach((container) => {
        if (container.chartInstance) {
            // Get the original config
            const configAttr = container.getAttribute('data-chart-config');
            const titleAttr = container.getAttribute('data-chart-title');
            const variableAttr = container.getAttribute('data-chart-variable');
            
            if (configAttr) {
                try {
                    const config = JSON.parse(configAttr);
                    if (titleAttr) {
                        config.title = titleAttr;
                    }
                    
                    // Destroy the old chart
                    container.chartInstance.destroy();
                    container.chartInstance = null;
                    
                    // Re-render with new theme
                    renderChart(container, config);
                } catch (e) {
                    console.error('Error updating chart:', e);
                }
            } else if (variableAttr) {
                try {
                    const config = window[variableAttr];
                    if (config) {
                        // Destroy the old chart
                        container.chartInstance.destroy();
                        container.chartInstance = null;
                        
                        // Re-render with new theme
                        renderChart(container, config);
                    }
                } catch (e) {
                    console.error('Error updating chart variable:', e);
                }
            }
        }
    });
}