// noinspection JSUnresolvedReference,HttpUrlsUsage,RequiredAttributes

/**
 * ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
 * ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
 * ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
 * ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
 * ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
 * ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
 * Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
 */

// Initialize Phantom modules namespace
window.PhantomModules = window.PhantomModules || {};

// Track initialization state in the global namespace to avoid redeclaration
window.PhantomModules.imageInitialized = window.PhantomModules.imageInitialized || false;

// Define initialization function for lazy loading
window.PhantomModules.initImage = function() {
    if (window.PhantomModules.imageInitialized) {
        console.log('[Phantom Image] Already initialized, skipping');
        return;
    }
    
    console.log('[Phantom Image] Initializing image component');
    window.PhantomModules.imageInitialized = true;
    
    // Initialize all image containers
    initializeImages();
    
    // Setup lightbox functionality
    setupLightbox();
    
    // Setup resize observer for responsive images
    setupResizeObserver();
};

// Also support traditional loading
document.addEventListener('DOMContentLoaded', function() {
    // Check if the function exists before calling
    if (window.PhantomModules && window.PhantomModules.initImage) {
        window.PhantomModules.initImage();
    }
});

/**
 * Resolve image path to ensure it points to the correct location
 * @param {string} path - The image path from data-src attribute
 * @returns {string} - The resolved absolute path
 */
function resolveImagePath(path) {
    if (!path) return '';
    
    // If path starts with http(s):// or /, it's already absolute
    if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('/')) {
        return path;
    }
    
    // If path contains ../, it's a relative path, keep as is
    if (path.includes('../')) {
        return path;
    }
    
    // Otherwise, assume it's relative to docs/assets/static/images/
    return '/assets/static/images/' + path;
}

/**
 * Initialize all image containers on the page
 */
function initializeImages() {
    const imageContainers = document.querySelectorAll('.phantom-image-container');
    
    if (imageContainers.length === 0) {
        console.log('[Phantom Image] No image containers found');
        return;
    }
    
    console.log(`[Phantom Image] Found ${imageContainers.length} image containers`);
    
    imageContainers.forEach((container, index) => {
        // Extract configuration from data attributes
        const config = {
            src: resolveImagePath(container.dataset.src),
            alt: container.dataset.alt || '',
            caption: container.dataset.caption,
            size: container.dataset.size || 'medium',
            position: container.dataset.position || 'center',
            loading: container.dataset.loading || 'lazy',
            lightbox: container.dataset.lightbox === 'true'
        };
        
        // Validate required attributes
        if (!config.src) {
            console.error(`[Phantom Image] Missing data-src for container ${index}`);
            showError(container, 'Missing image source');
            return;
        }
        
        // Create image element
        const img = document.createElement('img');
        img.className = 'phantom-image';
        img.alt = config.alt;
        
        // Add loading placeholder with Font Awesome spinner
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'phantom-image-loading';
        loadingDiv.innerHTML = `
            <i class="fas fa-spinner fa-spin" aria-hidden="true"></i>
            <span class="loading-text">Loading image...</span>
        `;
        container.appendChild(loadingDiv);
        
        // Set size class
        if (config.size && !container.classList.contains(config.size)) {
            container.classList.add(config.size);
        }
        
        // Store config in container for later use
        container._phantomConfig = config;
        
        // Handle image loading
        if (config.loading === 'lazy' && 'IntersectionObserver' in window) {
            setupLazyLoading(container, img, config);
        } else {
            loadImage(container, img, config);
        }
        
        // Setup lightbox if enabled
        if (config.lightbox) {
            container.style.cursor = 'zoom-in';
            container.setAttribute('tabindex', '0');
            container.setAttribute('role', 'button');
            container.setAttribute('aria-label', `View ${config.alt || 'image'} in fullscreen`);
            
            // Click handler
            container.addEventListener('click', (e) => {
                // Don't trigger on caption clicks or if image failed
                if (!e.target.classList.contains('phantom-image-caption') && 
                    !container.classList.contains('phantom-image-failed')) {
                    openLightbox(config.src, config.alt);
                }
            });
            
            // Keyboard handler
            container.addEventListener('keydown', (e) => {
                if ((e.key === 'Enter' || e.key === ' ') && 
                    !container.classList.contains('phantom-image-failed')) {
                    e.preventDefault();
                    openLightbox(config.src, config.alt);
                }
            });
        }
    });
}

/**
 * Setup lazy loading for an image
 */
function setupLazyLoading(container, img, config) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                console.log(`[Phantom Image] Loading lazy image: ${config.src}`);
                loadImage(container, img, config);
                observer.unobserve(container);
            }
        });
    }, {
        rootMargin: '50px' // Start loading 50px before entering viewport
    });
    
    observer.observe(container);
}

/**
 * Load an image into its container
 */
function loadImage(container, img, config) {
    // Set up load handler
    img.onload = function() {
        console.log(`[Phantom Image] Image loaded: ${config.src}`);
        
        // Remove loading placeholder
        const loading = container.querySelector('.phantom-image-loading');
        if (loading) {
            loading.remove();
        }
        
        // Add image to container
        container.appendChild(img);
        
        // Add caption only after successful load
        if (config.caption && !container.querySelector('.phantom-image-caption')) {
            const caption = document.createElement('div');
            caption.className = 'phantom-image-caption';
            caption.textContent = config.caption;
            container.appendChild(caption);
        }
        
        // Trigger loaded state with animation
        requestAnimationFrame(() => {
            img.classList.add('loaded');
        });
    };
    
    // Set up error handler
    img.onerror = function() {
        console.error(`[Phantom Image] Failed to load: ${config.src}`);
        showError(container, 'Failed to load image');
    };
    
    // Start loading
    img.src = config.src;
}

/**
 * Show error message in container
 */
function showError(container, message) {
    // Mark container as failed
    container.classList.add('phantom-image-failed');
    
    // Remove any existing captions to prevent them from showing with errors
    const existingCaption = container.querySelector('.phantom-image-caption');
    if (existingCaption) {
        existingCaption.remove();
    }
    
    const loading = container.querySelector('.phantom-image-loading');
    
    // Create error content with Font Awesome icon
    const errorContent = `
        <i class="fas fa-exclamation-triangle" aria-hidden="true"></i>
        <span>${message}</span>
    `;
    
    if (loading) {
        // Clear the loading content and replace with error
        loading.className = 'phantom-image-error';
        loading.innerHTML = errorContent;
    } else {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'phantom-image-error';
        errorDiv.innerHTML = errorContent;
        container.appendChild(errorDiv);
    }
}

/**
 * Setup lightbox functionality
 */
function setupLightbox() {
    // Check if lightbox already exists
    if (document.querySelector('.phantom-lightbox')) {
        return;
    }
    
    // Create lightbox container
    const lightbox = document.createElement('div');
    lightbox.className = 'phantom-lightbox';
    lightbox.innerHTML = `
        <img class="phantom-lightbox-image" alt="">
        <button class="phantom-lightbox-close" aria-label="Close lightbox">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        </button>
    `;
    
    document.body.appendChild(lightbox);
    
    // Close on click outside
    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox || e.target.classList.contains('phantom-lightbox-image')) {
            closeLightbox();
        }
    });
    
    // Close button
    lightbox.querySelector('.phantom-lightbox-close').addEventListener('click', closeLightbox);
    
    // Close on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && lightbox.classList.contains('active')) {
            closeLightbox();
        }
    });
}

/**
 * Open lightbox with image
 */
function openLightbox(src, alt) {
    console.log(`[Phantom Image] Opening lightbox: ${src}`);
    
    const lightbox = document.querySelector('.phantom-lightbox');
    const img = lightbox.querySelector('.phantom-lightbox-image');
    
    // Set loading state
    img.style.opacity = '0';
    img.src = src;
    img.alt = alt;
    
    // Show lightbox
    lightbox.classList.add('active');
    document.body.style.overflow = 'hidden';
    
    // Focus management for accessibility
    const previouslyFocused = document.activeElement;
    lightbox.setAttribute('data-previous-focus', '');
    lightbox.previouslyFocused = previouslyFocused;
    
    // Show image when loaded
    img.onload = function() {
        img.style.opacity = '1';
    };
    
    // Focus close button
    setTimeout(() => {
        lightbox.querySelector('.phantom-lightbox-close').focus();
    }, 100);
}

/**
 * Close lightbox
 */
function closeLightbox() {
    console.log('[Phantom Image] Closing lightbox');
    
    const lightbox = document.querySelector('.phantom-lightbox');
    const img = lightbox.querySelector('.phantom-lightbox-image');
    
    // Hide lightbox
    lightbox.classList.remove('active');
    document.body.style.overflow = '';
    
    // Clear image
    setTimeout(() => {
        img.src = '';
        img.style.opacity = '0';
    }, 300);
    
    // Restore focus
    if (lightbox.previouslyFocused) {
        lightbox.previouslyFocused.focus();
    }
}

/**
 * Setup resize observer for responsive behavior
 */
function setupResizeObserver() {
    if (!('ResizeObserver' in window)) {
        return;
    }
    
    const observer = new ResizeObserver(entries => {
        entries.forEach(entry => {
            const container = entry.target;
            const width = entry.contentRect.width;
            
            // Add responsive classes based on container width
            if (width < 300) {
                container.classList.add('phantom-image-narrow');
            } else {
                container.classList.remove('phantom-image-narrow');
            }
        });
    });
    
    // Observe all image containers
    document.querySelectorAll('.phantom-image-container').forEach(container => {
        observer.observe(container);
    });
}

// Export functions for external use
window.PhantomImage = {
    init: window.PhantomModules.initImage,
    open: openLightbox,
    close: closeLightbox
};

console.log('[Phantom Image] Module loaded');