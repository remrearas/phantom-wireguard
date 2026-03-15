/**
 * Language Switcher Script
 * Smart flag button language switching for Phantom WWW
 */

(function() {
    'use strict';

    // Language configuration
    const LANG_CONFIG = {
        'en': 'index.html',
        'tr': 'index-tr.html'
    };

    // Get current language from data attribute
    const languageSwitcher = document.querySelector('.language-switcher');
    if (!languageSwitcher) {
        console.warn('[Language Switcher] Element not found');
        return;
    }

    const currentLang = languageSwitcher.dataset.currentLang || 'en';
    console.log('[Language Switcher] Current language:', currentLang);

    // Get all language buttons
    const langButtons = document.querySelectorAll('.lang-btn');

    /**
     * Switch to a different language
     */
    function switchLanguage(targetLang) {
        if (targetLang === currentLang) {
            console.log('[Language Switcher] Already on', targetLang);
            return;
        }

        const targetFile = LANG_CONFIG[targetLang];
        if (!targetFile) {
            console.error('[Language Switcher] Unknown language:', targetLang);
            return;
        }

        console.log('[Language Switcher] Switching to', targetLang);

        // Save language preference
        try {
            localStorage.setItem('phantomPreferredLanguage', targetLang);
        } catch (e) {
            console.warn('[Language Switcher] Could not save preference:', e);
        }

        // Add loading state to clicked button
        const clickedButton = document.querySelector(`.lang-btn[data-lang="${targetLang}"]`);
        if (clickedButton) {
            clickedButton.classList.add('lang-btn-loading');
        }

        // Navigate to target language page
        window.location.href = targetFile;
    }

    /**
     * Handle language button clicks
     */
    langButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const targetLang = this.dataset.lang;

            if (targetLang && targetLang !== currentLang) {
                switchLanguage(targetLang);
            }
        });

        // Keyboard accessibility
        button.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const targetLang = this.dataset.lang;

                if (targetLang && targetLang !== currentLang) {
                    switchLanguage(targetLang);
                }
            }
        });
    });

    /**
     * Auto-apply saved language preference on page load
     */
    function applyLanguagePreference() {
        try {
            const preferredLang = localStorage.getItem('phantomPreferredLanguage');

            if (preferredLang && preferredLang !== currentLang && LANG_CONFIG[preferredLang]) {
                console.log('[Language Switcher] Auto-applying preference:', preferredLang);

                // Only redirect if we're not already navigating
                if (!window.location.href.includes('?')) {
                    switchLanguage(preferredLang);
                }
            }
        } catch (e) {
            console.warn('[Language Switcher] Could not read preference:', e);
        }
    }

    // Apply preference on initial load (but not on page reload/navigation)
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyLanguagePreference);
    }

    console.log('[Language Switcher] Initialized with', langButtons.length, 'buttons');
})();