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

// YouTube Player initialization for MkDocs

// Helper function to get player options from element attributes
function getYouTubePlayerOptions(element) {
    return {
        videoId: element.getAttribute('data-video-id'),
        autoplay: element.getAttribute('data-autoplay') === 'true' ? 1 : 0,
        controls: element.getAttribute('data-controls') !== 'false' ? 1 : 0,
        loop: element.getAttribute('data-loop') === 'true' ? 1 : 0,
        start: parseInt(element.getAttribute('data-start')) || 0,
        end: parseInt(element.getAttribute('data-end')) || 0,
        mute: element.getAttribute('data-mute') === 'true' ? 1 : 0,
        rel: element.getAttribute('data-rel') === 'true' ? 1 : 0,
        modestbranding: element.getAttribute('data-modestbranding') !== 'false' ? 1 : 0
    };
}

// Helper function to build YouTube embed URL
function buildYouTubeEmbedUrl(options) {
    const params = new URLSearchParams({
        autoplay: options.autoplay,
        controls: options.controls,
        loop: options.loop,
        mute: options.mute,
        rel: options.rel,
        modestbranding: options.modestbranding,
        origin: window.location.origin
    });
    
    if (options.start > 0) {
        params.append('start', options.start);
    }
    
    if (options.end > 0) {
        params.append('end', options.end);
    }
    
    if (options.loop === 1) {
        params.append('playlist', options.videoId);
    }
    
    return `https://www.youtube-nocookie.com/embed/${options.videoId}?${params.toString()}`;
}

// Helper function to create YouTube iframe
function createYouTubeIframe(element, options) {
    // Add loading state and spinner
    element.classList.add('loading');
    const spinner = document.createElement('div');
    spinner.className = 'player-spinner';
    spinner.innerHTML = '<div class="spinner-inner"></div>';
    element.appendChild(spinner);
    
    const iframe = document.createElement('iframe');
    iframe.src = buildYouTubeEmbedUrl(options);
    iframe.width = '100%';
    iframe.height = '100%';
    iframe.style.border = '0';
    iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
    iframe.allowFullscreen = true;
    iframe.loading = 'lazy';
    iframe.title = 'YouTube video player';
    
    // Handle iframe load event
    iframe.addEventListener('load', function() {
        // Remove loading state when iframe is loaded
        element.classList.remove('loading');
        if (spinner.parentNode) {
            spinner.remove();
        }
    });
    
    // Handle iframe error
    iframe.addEventListener('error', function() {
        console.error('YouTube iframe failed to load');
        element.classList.remove('loading');
        if (spinner.parentNode) {
            spinner.remove();
        }
        element.innerHTML = '<div class="youtube-error">Failed to load YouTube video</div>';
    });
    
    // Create responsive container
    const container = document.createElement('div');
    container.className = 'youtube-player-responsive';
    container.appendChild(iframe);
    
    element.appendChild(container);
}

document.addEventListener('DOMContentLoaded', function() {
    // Find all YouTube player elements
    const playerElements = document.querySelectorAll('.youtube-player');
    
    playerElements.forEach(function(element) {
        const videoId = element.getAttribute('data-video-id');
        
        // Set ID if not already set
        if (!element.id) {
            element.id = 'youtube-player-' + Math.random().toString(36).substring(2, 11);
        }
        
        if (!videoId) {
            console.error('No video ID specified for YouTube player element');
            element.innerHTML = '<div class="youtube-error">No video ID provided</div>';
            return;
        }
        
        // Get player configuration
        const playerOptions = getYouTubePlayerOptions(element);
        
        // Create player
        try {
            createYouTubeIframe(element, playerOptions);
        } catch (error) {
            console.error('Failed to create YouTube player:', error);
            element.innerHTML = '<div class="youtube-error">Failed to load YouTube video</div>';
        }
    });
});

// Handle dynamic content (e.g., when switching tabs)
if (typeof MutationObserver !== 'undefined') {
    // Helper function to initialize a player element
    function initializeYouTubePlayer(element) {
        const videoId = element.getAttribute('data-video-id');
        if (videoId) {
            element.classList.add('initialized');
            
            // Get player configuration
            const playerOptions = getYouTubePlayerOptions(element);
            
            try {
                createYouTubeIframe(element, playerOptions);
            } catch (error) {
                console.error('Failed to create YouTube player:', error);
            }
        }
    }
    
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) { // Element node
                    const players = node.querySelectorAll ? node.querySelectorAll('.youtube-player:not(.initialized)') : [];
                    players.forEach(initializeYouTubePlayer);
                }
            });
        });
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
}