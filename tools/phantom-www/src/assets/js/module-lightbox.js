/**
 * Phantom Module Lightbox
 * Interactive modal for module details
 */

window.PhantomLightbox = (function() {
    'use strict';

    let currentModule = null;
    let isOpen = false;

    /**
     * Initialize lightbox
     */
    function init() {
        setupEventListeners();
    }

    /**
     * Open lightbox with specific module
     */
    async function open(moduleId) {
        if (isOpen) return;

        currentModule = moduleId;
        const lightbox = document.getElementById('moduleLightbox');
        const lightboxInner = document.getElementById('lightboxInner');
        const template = document.getElementById(`${moduleId}-template`);

        if (!lightbox || !lightboxInner || !template) {
            console.error('Lightbox elements not found');
            return;
        }

        // Clear previous content
        lightboxInner.innerHTML = '';

        // Show loading state
        lightboxInner.classList.add('lightbox-loading');

        // Add active class
        lightbox.classList.add('active');
        document.body.classList.add('lightbox-open');

        // Prevent body scroll on mobile
        document.body.style.overflow = 'hidden';
        document.body.style.position = 'fixed';
        document.body.style.width = '100%';

        isOpen = true;

        // Wait for animation to establish
        await waitForAnimation(300);

        // Remove loading state
        lightboxInner.classList.remove('lightbox-loading');

        // Clone and insert template content
        const content = template.content.cloneNode(true);
        lightboxInner.appendChild(content);

        // Animate content
        await animateContentEntry();
    }

    /**
     * Close lightbox
     */
    async function close() {
        if (!isOpen) return;

        const lightbox = document.getElementById('moduleLightbox');
        const lightboxInner = document.getElementById('lightboxInner');

        // Add closing animation
        lightbox.style.animation = 'fadeOut 0.3s ease-out';

        // Wait for animation to complete
        await waitForAnimation(300);

        // Clean up after animation
        lightbox.classList.remove('active');
        lightbox.style.animation = '';
        document.body.classList.remove('lightbox-open');

        // Restore body scroll
        document.body.style.overflow = '';
        document.body.style.position = '';
        document.body.style.width = '';

        lightboxInner.innerHTML = '';
        isOpen = false;
        currentModule = null;
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Close button click handler
        const closeBtn = document.querySelector('.lightbox-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                close().catch(error => {
                    console.error('Error closing lightbox:', error);
                });
            });
        }

        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isOpen) {
                close().catch(error => {
                    console.error('Error closing lightbox:', error);
                });
            }
        });

        // Navigate between modules with arrow keys
        document.addEventListener('keydown', async (e) => {
            if (!isOpen) return;

            const modules = ['core', 'ghost', 'multihop', 'multighost'];
            const currentIndex = modules.indexOf(currentModule);

            if (e.key === 'ArrowRight' && currentIndex < modules.length - 1) {
                await close();
                await open(modules[currentIndex + 1]);
            } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
                await close();
                await open(modules[currentIndex - 1]);
            }
        });

        // Prevent scroll on body when lightbox is open
        document.addEventListener('wheel', (e) => {
            if (isOpen && !e.target.closest('.lightbox-inner')) {
                e.preventDefault();
            }
        }, { passive: false });
    }

    /**
     * Wait for animation or transition
     */
    function waitForAnimation(duration) {
        return new Promise(resolve => setTimeout(resolve, duration));
    }

    /**
     * Animate content entry
     */
    async function animateContentEntry() {
        const elements = document.querySelectorAll('.module-description-container');

        // Prepare all elements
        elements.forEach((el) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'all 0.5s ease-out';
        });

        // Animate each element with async delay
        for (let i = 0; i < elements.length; i++) {
            if (i > 0) {
                await waitForAnimation(100); // Stagger delay between elements
            }
            elements[i].style.opacity = '1';
            elements[i].style.transform = 'translateY(0)';
        }
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            init();
        });
    } else {
        init();
    }

    // Add fade out animation if not exists
    if (!document.querySelector('style[data-lightbox-animations]')) {
        const style = document.createElement('style');
        style.setAttribute('data-lightbox-animations', 'true');
        style.textContent = `
            @keyframes fadeOut {
                from { opacity: 1; }
                to { opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }

    // Public API
    return {
        open,
        close
    };

})();

// Auto-init module cards click handlers
document.addEventListener('DOMContentLoaded', () => {
    // Remove onclick from HTML and add event listeners here for better practice
    const moduleCards = document.querySelectorAll('.module-card[data-module]');

    moduleCards.forEach(card => {
        const moduleId = card.dataset.module;

        card.style.cursor = 'pointer';

        // Remove any existing onclick attribute
        card.removeAttribute('onclick');

        // Add click event listener
        card.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            // Handle the promise but don't need to do anything with it
            PhantomLightbox.open(moduleId).catch(error => {
                console.error('Error opening lightbox:', error);
            });
        });

        // Visual feedback on click
        card.addEventListener('mousedown', () => {
            card.style.transform = 'scale(0.98)';
        });

        card.addEventListener('mouseup', () => {
            card.style.transform = '';
        });
    });
});