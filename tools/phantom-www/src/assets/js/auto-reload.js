/**
 * Auto-reload Development Script
 * Uses Server-Sent Events (SSE) to reload the page when files change
 * Only active in development mode
 */

(function() {
    'use strict';

    // Configuration
    const SSE_ENDPOINT = '/sse';
    const INITIAL_RECONNECT_DELAY = 500; // Start with 500ms
    const MAX_RECONNECT_DELAY = 5000; // Max 5 seconds

    let reconnectAttempts = 0;
    let eventSource = null;
    let reconnectTimeout = null;

    /**
     * Initialize SSE connection
     */
    function connect() {
        console.log('[Auto-Reload] Attempting to connect to SSE endpoint...');

        // Close existing connection if any
        if (eventSource) {
            console.log('[Auto-Reload] Closing existing connection');
            eventSource.close();
        }

        // Create new EventSource connection
        try {
            eventSource = new EventSource(SSE_ENDPOINT);
            console.log('[Auto-Reload] EventSource created, waiting for connection...');
        } catch (error) {
            console.error('[Auto-Reload] Failed to create EventSource:', error);
            return;
        }

        // Connection opened
        eventSource.addEventListener('open', function() {
            console.log('[Auto-Reload] ✓ Connected to development server');
            reconnectAttempts = 0;
        });

        // Init event - server just started
        eventSource.addEventListener('init', function() {
            console.log('[Auto-Reload] Server initialized');

            // Only reload if page was already loaded (restart scenario)
            // Prevent infinite loop by checking when page was last loaded
            const now = Date.now();
            const lastLoadTime = parseInt(localStorage.getItem('autoReloadLastLoad') || '0');
            const timeSinceLoad = now - lastLoadTime;

            // Only reload if:
            // 1. Page is fully loaded (document.readyState === 'complete')
            // 2. Page was loaded more than 5 seconds ago (not a fresh reload)
            if (document.readyState === 'complete' && timeSinceLoad > 5000) {
                console.log('[Auto-Reload] Server restarted, reloading page...');
                showReloadNotification();

                // Store reload time before reloading
                localStorage.setItem('autoReloadLastLoad', String(now));

                setTimeout(function() {
                    window.location.reload();
                }, 300);
            } else if (timeSinceLoad <= 5000) {
                console.log('[Auto-Reload] Page just loaded, skipping reload to prevent loop');
            }
        });

        // Reload event received
        eventSource.addEventListener('reload', function(e) {
            console.log('[Auto-Reload] Reload triggered:', e.data);

            // Show visual feedback
            showReloadNotification();

            // Reload immediately (connection will close automatically)
            window.location.reload();
        });

        // Connection error
        eventSource.addEventListener('error', function() {
            console.warn('[Auto-Reload] Connection error');
            eventSource.close();

            // Clear any existing reconnect timeout
            if (reconnectTimeout) {
                clearTimeout(reconnectTimeout);
            }

            // Calculate exponential backoff delay
            reconnectAttempts++;
            const delay = Math.min(
                INITIAL_RECONNECT_DELAY * Math.pow(1.5, reconnectAttempts - 1),
                MAX_RECONNECT_DELAY
            );

            console.log(`[Auto-Reload] Reconnecting in ${Math.round(delay)}ms (attempt ${reconnectAttempts})...`);

            // Schedule reconnection
            reconnectTimeout = setTimeout(connect, delay);
        });
    }

    /**
     * Show visual notification when reload is triggered
     */
    function showReloadNotification() {
        // Create notification element
        const notification = document.createElement('div');
        notification.textContent = 'Reloading...';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #4CAF50;
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
            z-index: 999999;
            animation: slideIn 0.3s ease-out;
        `;

        // Add animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(400px);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(notification);
    }

    /**
     * Initialize when DOM is ready
     */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            // Mark page load time when DOM is ready
            localStorage.setItem('autoReloadLastLoad', String(Date.now()));
            connect();
        });
    } else {
        // Page already loaded, mark the time
        localStorage.setItem('autoReloadLastLoad', String(Date.now()));
        connect();
    }

    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
        }
        if (eventSource) {
            eventSource.close();
        }
    });

    console.log('[Auto-Reload] Development auto-reload enabled');
})();