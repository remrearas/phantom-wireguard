#!/usr/bin/env python3
"""
Phantom WWW Development Server
Watch for changes and serve with live reload
"""

import sys
import os
import logging
import yaml
import http.server
import socketserver
import tempfile
import shutil
import atexit
import threading
import time
import signal
from pathlib import Path
from textwrap import dedent
from typing import Optional
from watchdog.observers import Observer

# Add builder to path
sys.path.insert(0, str(Path(__file__).parent))

from builder.content import ContentProcessor
from builder.templates import TemplateRenderer
from builder.assets import AssetProcessor


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# Load configuration
config = load_config()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config['logging']['level']),
    format=config['logging']['format'],
    datefmt=config['logging']['date_format']
)
logger = logging.getLogger(__name__)


def print_banner():
    """Display Phantom WWW banner"""
    banner = dedent("""
        ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
        ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
        ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
        ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
        ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
        ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

        WWW Development Server - Live Reload & Watch
        Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
    """).strip()

    # Print banner without timestamp
    print(banner)
    print()


class SSEManager:
    """Manages Server-Sent Events connections for auto-reload"""

    def __init__(self):
        self.clients = []
        self.lock = threading.Lock()

    def add_client(self, client):
        """Add a new SSE client"""
        with self.lock:
            self.clients.append(client)
            logger.info(f"SSE client connected (total: {len(self.clients)})")

    def remove_client(self, client):
        """Remove an SSE client"""
        with self.lock:
            if client in self.clients:
                self.clients.remove(client)
                logger.info(f"SSE client disconnected (total: {len(self.clients)})")

    def broadcast_reload(self):
        """Send reload event to all connected clients"""
        with self.lock:
            dead_clients = []
            for client in self.clients:
                try:
                    message = f"event: reload\ndata: {time.time()}\n\n"
                    client.wfile.write(message.encode('utf-8'))
                    client.wfile.flush()
                    # Mark client for disconnection
                    client.should_disconnect = True
                except (BrokenPipeError, ConnectionResetError):
                    dead_clients.append(client)

            # Remove dead clients
            for client in dead_clients:
                self.clients.remove(client)

            if self.clients:
                logger.info(f"Sent reload event to {len(self.clients)} client(s)")


# Global SSE manager instance
sse_manager = SSEManager()

# Global shutdown flag
shutdown_event = threading.Event()

# Global resources for cleanup
observer_instance: Optional[Observer] = None
httpd_instance: Optional[socketserver.ThreadingTCPServer] = None
temp_dir_path: Optional[str] = None
cleanup_done = False


def cleanup_resources():
    """Clean up all resources gracefully"""
    global observer_instance, httpd_instance, temp_dir_path, cleanup_done

    # Prevent duplicate cleanup
    if cleanup_done:
        return
    cleanup_done = True

    logger.info("Shutting down gracefully...")

    # Stop HTTP server first (prevent new connections)
    if httpd_instance:
        try:
            # Shutdown must be called from a different thread to avoid deadlock
            def shutdown_server():
                httpd_instance.shutdown()
                httpd_instance.server_close()
                logger.info("HTTP server stopped")

            shutdown_thread = threading.Thread(target=shutdown_server, daemon=True)
            shutdown_thread.start()
            shutdown_thread.join(timeout=1.0)
        except (AttributeError, OSError) as e:
            logger.error(f"Error stopping HTTP server: {e}")

    # Disconnect all SSE clients
    with sse_manager.lock:
        for client in sse_manager.clients[:]:
            try:
                client.should_disconnect = True
            except (AttributeError, OSError):
                pass
        sse_manager.clients.clear()
        logger.info("Disconnected all SSE clients")

    # Give threads a moment to exit gracefully
    time.sleep(0.2)

    # Stop file watcher
    if observer_instance:
        try:
            observer_instance.stop()
            observer_instance.join(timeout=2)
            logger.info("File watcher stopped")
        except (AttributeError, RuntimeError) as e:
            logger.error(f"Error stopping file watcher: {e}")

    # Clean up temp directory
    if temp_dir_path and Path(temp_dir_path).exists():
        try:
            shutil.rmtree(temp_dir_path)
            logger.info(f"Cleaned up temporary directory: {temp_dir_path}")
        except (OSError, PermissionError) as e:
            logger.error(f"Error cleaning temp directory: {e}")


def signal_handler(signum: int, _) -> None:
    """Handle shutdown signals"""
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name} signal")
    shutdown_event.set()
    cleanup_resources()
    # Force immediate exit without triggering finally block or atexit
    os._exit(0)


class PhantomDevServer:
    def __init__(self, src_dir, dist_dir, assets_dir):
        self.src_dir = Path(src_dir)
        self.dist_dir = Path(dist_dir)
        self.assets_dir = Path(assets_dir)

        # Initialize processors for dev environment
        self.content_processor = ContentProcessor(self.src_dir / 'content')
        self.template_renderer = TemplateRenderer(self.src_dir / 'templates')
        self.asset_processor = AssetProcessor(self.assets_dir, env='dev')

    def build(self, language='en'):
        """Build for a specific language"""
        logger.info(f"Building {language.upper()} version")

        # Process markdown content
        content = self.content_processor.process_all(language)

        # Render module cards and details
        for module in content['modules']:
            module['card_html'] = self.template_renderer.render_module_card(module)
            module['detail_html'] = self.template_renderer.render_module_detail(module)

        # Render main template
        html = self.template_renderer.render('index.template.j2', {
            'lang': language,
            'env': 'dev',
            **content
        })

        # Write output (default language gets index.html, others get index-{lang}.html)
        default_lang = config['languages'][0]
        output_file = 'index.html' if language == default_lang else f'index-{language}.html'
        output_path = self.dist_dir / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Built {output_file}")

    def build_all_languages(self):
        """Build all languages"""
        for lang in config['languages']:
            try:
                self.build(lang)
            except Exception as e:
                logger.error(f"Error building {lang}: {e}")
                import traceback
                traceback.print_exc()
                continue

        # Copy assets
        self.asset_processor.copy_to_dist(self.dist_dir)

    def watch(self):
        """Watch for changes and rebuild"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class BuildHandler(FileSystemEventHandler):
                def __init__(self, server):
                    self.server = server
                    self.last_build_time = 0

                def on_modified(self, event):
                    # Debounce rapid changes
                    import time
                    current_time = time.time()
                    debounce_time = config['build']['debounce_time']
                    if current_time - self.last_build_time < debounce_time:
                        return

                    # Only rebuild for relevant file types
                    watch_exts = tuple(config['build']['watch_extensions'])
                    if event.src_path.endswith(watch_exts):
                        logger.info(f"Change detected: {event.src_path}")
                        try:
                            self.server.build_all_languages()
                            logger.info("Rebuild completed")

                            # Notify connected browsers to reload
                            sse_manager.broadcast_reload()
                        except Exception as e:
                            logger.error(f"Build error: {e}")

                        self.last_build_time = current_time

            observer = Observer()
            observer.schedule(BuildHandler(self), str(self.src_dir), recursive=True)
            observer.start()

            logger.info("File watcher started")
            return observer

        except ImportError:
            logger.error("watchdog not installed. Install with: pip install watchdog")
            sys.exit(1)

    def serve(self):
        """Start HTTP server"""
        global httpd_instance

        # Change to dist directory
        os.chdir(self.dist_dir)

        # Create HTTP server
        handler = http.server.SimpleHTTPRequestHandler

        # Custom handler to suppress logs and handle SSE
        class QuietHandler(handler):
            def __init__(self, *args, **kwargs):
                """Initialize handler with disconnect flag"""
                self.should_disconnect = False
                try:
                    super().__init__(*args, **kwargs)
                except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                    # Client closed connection during initialization, ignore silently
                    pass

            def do_GET(self):
                """Handle GET requests"""
                # Handle SSE endpoint
                if self.path == '/sse':
                    self.handle_sse()
                    return

                # Default file serving
                super().do_GET()

            def handle_sse(self):
                """Handle Server-Sent Events connection"""
                # Send SSE headers
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                # Reset disconnect flag for this SSE connection
                self.should_disconnect = False

                # Add client to SSE manager
                sse_manager.add_client(self)

                # Send init event on first connection
                try:
                    init_message = f"event: init\ndata: {time.time()}\n\n"
                    self.wfile.write(init_message.encode('utf-8'))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    sse_manager.remove_client(self)
                    return

                # Keep connection alive with periodic heartbeats
                try:
                    heartbeat_counter = 0
                    while not self.should_disconnect:
                        # Check disconnect flag every 0.1 second for quick shutdown
                        time.sleep(0.1)
                        if self.should_disconnect:
                            break

                        # Send heartbeat every 15 seconds (150 iterations)
                        heartbeat_counter += 1
                        if heartbeat_counter >= 150:
                            self.wfile.write(b": heartbeat\n\n")
                            self.wfile.flush()
                            heartbeat_counter = 0
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    sse_manager.remove_client(self)

            def log_message(self, fmt, *args):
                # Only log errors (not SSE connections)
                if not args[1].startswith('2') and self.path != '/sse':
                    logger.info(f"{args[0]} - {args[1]}")

        server_host = config['server']['host']
        server_port = config['server']['port']

        try:
            # Allow immediate port reuse
            socketserver.ThreadingTCPServer.allow_reuse_address = True

            httpd = socketserver.ThreadingTCPServer((server_host, server_port), QuietHandler)
            httpd_instance = httpd  # Set global instance for cleanup
            with httpd:
                # noinspection HttpUrlsUsage
                logger.info(f"HTTP server started at http://{server_host}:{server_port}")
                logger.info(f"Serving directory: {self.dist_dir.absolute()}")
                logger.info("Press Ctrl+C to stop")
                print()
                httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server stopped")
            print()
        except OSError as e:
            logger.error(f"Failed to start server: {e}")
            logger.error(f"Port {server_port} may already be in use")
            sys.exit(1)


def main():
    global observer_instance, httpd_instance, temp_dir_path

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Display banner
    print_banner()

    # Get project root
    project_root = Path(__file__).parent

    # Create temporary directory for development build
    temp_dir = tempfile.mkdtemp(prefix='phantom-www-')
    temp_dir_path = temp_dir  # Set global variable
    logger.info(f"Created temporary build directory: {temp_dir}")
    print()

    # Register cleanup function as fallback
    atexit.register(cleanup_resources)

    # Initialize dev server
    server = PhantomDevServer(
        src_dir=project_root / 'src',
        dist_dir=Path(temp_dir),
        assets_dir=project_root / 'src' / 'assets'
    )

    # Initial build
    logger.info("Building initial version")
    server.build_all_languages()
    logger.info("Initial build completed")
    print()

    # Start file watcher in background
    observer_instance = server.watch()  # Set global variable

    # Start HTTP server (blocking)
    try:
        server.serve()
    finally:
        # Cleanup on exit
        cleanup_resources()


if __name__ == '__main__':
    main()