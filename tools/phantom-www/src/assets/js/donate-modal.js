/**
 * Phantom Donate Modal
 * Interactive modal for cryptocurrency donations
 */

window.PhantomDonate = (function() {
    'use strict';

    let isOpen = false;

    /**
     * Initialize donate modal
     */
    function init() {
        setupEventListeners();
    }

    /**
     * Open donate modal
     */
    async function open() {
        if (isOpen) return;

        const donateModal = document.getElementById('donateModal');
        if (!donateModal) {
            console.error('Donate modal not found');
            return;
        }

        // Add active class
        donateModal.classList.add('active');
        document.body.classList.add('lightbox-open');

        // Prevent body scroll
        document.body.style.overflow = 'hidden';
        document.body.style.position = 'fixed';
        document.body.style.width = '100%';

        isOpen = true;

        // Animate content entry
        await animateContentEntry();
    }

    /**
     * Close donate modal
     */
    async function close() {
        if (!isOpen) return;

        const donateModal = document.getElementById('donateModal');

        // Add closing animation
        donateModal.style.animation = 'fadeOut 0.3s ease-out';

        // Wait for animation to complete
        await waitForAnimation(300);

        // Clean up after animation
        donateModal.classList.remove('active');
        donateModal.style.animation = '';
        document.body.classList.remove('lightbox-open');

        // Restore body scroll
        document.body.style.overflow = '';
        document.body.style.position = '';
        document.body.style.width = '';

        isOpen = false;
    }

    /**
     * Copy crypto address to clipboard
     */
    async function copyAddress(cryptoType) {
        const addressId = cryptoType === 'btc' ? 'btcAddress' : 'xmrAddress';
        const addressElement = document.getElementById(addressId);
        const copyBtn = document.querySelector(`.crypto-copy-btn[data-crypto="${cryptoType}"]`);

        if (!addressElement || !copyBtn) {
            console.error('Address element or copy button not found');
            return;
        }

        const address = addressElement.textContent;

        try {
            // Copy to clipboard
            await navigator.clipboard.writeText(address);

            // Visual feedback
            copyBtn.classList.add('copied');

            // Change icon to check temporarily
            const iconUse = copyBtn.querySelector('.phantom-icon use');
            const originalHref = iconUse.getAttribute('href');
            iconUse.setAttribute('href', 'assets/icons/sprite.svg#icon-check');

            // Reset after 2 seconds
            setTimeout(() => {
                copyBtn.classList.remove('copied');
                iconUse.setAttribute('href', originalHref);
            }, 2000);

            console.log(`${cryptoType.toUpperCase()} address copied to clipboard`);
        } catch (error) {
            console.error('Failed to copy address:', error);

            // Fallback for older browsers that don't support Clipboard API
            try {
                const textarea = document.createElement('textarea');
                textarea.value = address;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                // noinspection JSDeprecatedSymbols - Intentional fallback for older browsers
                document.execCommand('copy');
                document.body.removeChild(textarea);

                // Still show visual feedback
                copyBtn.classList.add('copied');
                setTimeout(() => copyBtn.classList.remove('copied'), 2000);
            } catch (fallbackError) {
                console.error('Fallback copy also failed:', fallbackError);
            }
        }
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Support Me link click handler
        const supportMeLink = document.getElementById('supportMeLink');
        if (supportMeLink) {
            supportMeLink.addEventListener('click', (e) => {
                e.preventDefault();
                open().catch(error => {
                    console.error('Error opening donate modal:', error);
                });
            });
        }

        // Close button click handler (for donate modal)
        const donateModal = document.getElementById('donateModal');
        if (donateModal) {
            const closeBtn = donateModal.querySelector('.lightbox-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    close().catch(error => {
                        console.error('Error closing donate modal:', error);
                    });
                });
            }
        }

        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isOpen) {
                close().catch(error => {
                    console.error('Error closing donate modal:', error);
                });
            }
        });

        // Copy button handlers
        const copyButtons = document.querySelectorAll('.crypto-copy-btn');
        copyButtons.forEach(btn => {
            const cryptoType = btn.dataset.crypto;
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                copyAddress(cryptoType).catch(error => {
                    console.error('Error copying address:', error);
                });
            });
        });
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
        const elements = document.querySelectorAll('.crypto-card');

        // Prepare all elements
        elements.forEach((el) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'all 0.5s ease-out';
        });

        // Small initial delay
        await waitForAnimation(100);

        // Animate each element with stagger
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

    // Public API
    return {
        open,
        close
    };

})();