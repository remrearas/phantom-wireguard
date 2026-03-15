/**
 * ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
 * ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
 * ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
 * ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
 * ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
 * ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
 * Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
 */

(function() {
    'use strict';
    
    /**
     * Extract base path without language prefix
     */
    function extractBasePath(path, languages) {
        // Remove leading and trailing slashes for easier processing
        let normalizedPath = path.replace(/^\//, '').replace(/\/$/, '');
        
        // Check each non-default language
        for (const lang of languages) {
            if (!lang.default) {
                const langCode = lang.code;
                
                // Check if path is exactly the language code or starts with it
                if (normalizedPath === langCode) {
                    return '';
                } else if (normalizedPath.startsWith(langCode + '/')) {
                    return normalizedPath.substring(langCode.length + 1);
                }
            }
        }
        
        // Path doesn't have language prefix
        return normalizedPath;
    }
    
    /**
     * Build clean URL from site URL and path
     */
    function buildUrl(siteUrl, path) {
        const cleanSiteUrl = siteUrl.replace(/\/$/, '');
        const cleanPath = path.replace(/^\//, '').replace(/\/$/, '');
        
        if (!cleanPath) {
            return cleanSiteUrl + '/';
        } else {
            return cleanSiteUrl + '/' + cleanPath + '/';
        }
    }
    
    /**
     * Generate and insert hreflang links
     */
    function generateHreflangLinks() {
        // Check if configuration exists
        if (!window.hreflangConfig || !window.hreflangConfig.languages) {
            console.warn('Hreflang configuration not found');
            return;
        }
        
        // Don't generate on 404 or error pages
        if (!document.querySelector('link[rel="canonical"]')) {
            return;
        }
        
        const config = window.hreflangConfig;
        const basePath = extractBasePath(config.currentUrl || '', config.languages);
        const headElement = document.head;
        
        // Remove any existing hreflang links (in case of dynamic updates)
        const existingHreflang = document.querySelectorAll('link[rel="alternate"][hreflang]');
        existingHreflang.forEach(link => link.remove());
        
        // Generate hreflang for each language
        config.languages.forEach(lang => {
            const link = document.createElement('link');
            link.rel = 'alternate';
            link.hreflang = lang.code;
            
            if (lang.default) {
                // Default language doesn't need prefix
                link.href = buildUrl(config.siteUrl, basePath);
            } else {
                // Non-default languages need their prefix
                if (basePath) {
                    link.href = buildUrl(config.siteUrl, lang.code + '/' + basePath);
                } else {
                    link.href = buildUrl(config.siteUrl, lang.code);
                }
            }
            
            headElement.appendChild(link);
        });
        
        // Add x-default pointing to default language
        const defaultLang = config.languages.find(l => l.default);
        if (defaultLang) {
            const xDefaultLink = document.createElement('link');
            xDefaultLink.rel = 'alternate';
            xDefaultLink.hreflang = 'x-default';
            xDefaultLink.href = buildUrl(config.siteUrl, basePath);
            headElement.appendChild(xDefaultLink);
        }
        
        // Debug info (remove in production)
        console.log('Hreflang Generator:', {
            currentUrl: config.currentUrl,
            basePath: basePath,
            siteUrl: config.siteUrl,
            languages: config.languages,
            generated: document.querySelectorAll('link[rel="alternate"][hreflang]').length + ' links'
        });
    }
    
    // Make function globally available
    window.generateHreflangLinks = generateHreflangLinks;
    
    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', generateHreflangLinks);
    } else {
        generateHreflangLinks();
    }
})();