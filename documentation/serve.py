#!/usr/bin/env python3
"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>

TR: Phantom Documentation Kit Geliştirme Sunucusu (serve.py)
=================================================

Bu script, Phantom Documentation Kit için esnek ve güçlü bir geliştirme sunucusu sağlar.
Üç farklı modda çalışabilir: Native (yerel), Local Docker ve Remote Docker. Her mod, 
farklı senaryolar için optimize edilmiş benzersiz avantajlar sunar.

Benzer şekilde çalışan farklı entegrasyonlarınız içinde çalışan stabil bir örnek oluşturulabilir.

Çalışma Modları:
---------------

1. Native Mode (Local Mod):
   Komut: python serve.py
   User → serve.py → MkDocs Server → Browser
   - Doğrudan yerel makinede çalışır
   - En hızlı başlatma süresi
   - Python ve Node.js kurulumu gerektirir
   - Vendor dosyaları kontrolü ve otomatik derleme, optimizasyon

2. Local Docker Mode:
   Komut: python serve.py --docker
   User → serve.py → Docker Container → MkDocs Server → Browser
   - Yerel Docker daemon kullanır
   - İzole edilmiş ortam sağlar
   - Bağımlılık yönetimi kolaylığı
   - Volume mount ile dosya senkronizasyonu

3. Remote Docker Mode:
   Komut: DOCKER_HOST=ssh://user@server && python serve.py --docker
   User → serve.py → SSH → Remote Docker → Container → MkDocs Server
   Local Files ←→ Mutagen Sync ←→ Container Files
   - Uzak sunucudaki Docker daemon'a bağlanır
   - Mutagen ile bidirectional (çift-yönlü) dosya senkronizasyonu
   - Mutagen Port forwarding özelliği ile local ve güvenli erişim
   - SSH üzerinden güvenli bağlantı (Tavsiye edilen yöntem)

Mutagen Entegrasyonu:
-------------------
Remote Docker modunda Mutagen kritik rol oynar:

1. Senkronizasyon Kurulumu:
   - Yerel dizin ↔ Uzak container arasında bidirectional (çift-yönlü) sync
   - Otomatik değişiklik algılama ve uzak sunucudaki container ile senkronizasyon
   - Akıllı fine-tuned ignore pattern'ları (node_modules, .git, vb.)

2. Port Forwarding:
   - Container portları → Yerel portlar
   - MkDocs sunucusuna yerel erişim (localhost:8000)

3. Performans Optimizasyonu:
   - Delta senkronizasyonu (sadece değişiklikler)
   - Conflict resolution mekanizması
   - Staging → Transitioning → Watching döngüsü

Ana Fonksiyonlar:
----------------
- check_vendor_files(): Vendor bağımlılıklarını kontrol eder. (tools/vendor-builder)
- build_vendor_files(): Eksik vendor dosyalarını derler. (tools/vendor-builder)
- serve_docs(): MkDocs sunucusunu başlatır
- native_serve(): Yerel modda çalıştırır
- docker_serve(): Docker modunda çalıştırır (local veya remote)

Ortam Değişkenleri:
------------------
- DOCKER_MODE: Docker container içinde çalışıyor mu?
- DOCKER_HOST: Remote Docker daemon adresi (ssh://user@host)
- DOCKER_REMOTE_SERVE: Remote Docker serve modu aktif mi?

==================================================
EN: Phantom Documentation Kit Development Server (serve.py)
================================================

This script provides a flexible and powerful development server for Phantom Documentation 
Kit. It can operate in three different modes: Native (local), Local Docker, and Remote 
Docker. Each mode offers unique advantages optimized for different scenarios.

It can also create a stable example for your different integrations working in a similar manner.

Operating Modes:
---------------

1. Native Mode (Local Mode):
   Command: python serve.py
   User → serve.py → MkDocs Server → Browser
   - Runs directly on local machine
   - Fastest startup time
   - Requires Python and Node.js installation
   - Vendor file checking and automatic compilation, optimization

2. Local Docker Mode:
   Command: python serve.py --docker
   User → serve.py → Docker Container → MkDocs Server → Browser
   - Uses local Docker daemon
   - Provides isolated environment
   - Easy dependency management
   - File synchronization via volume mounts

3. Remote Docker Mode:
   Command: DOCKER_HOST=ssh://user@server && python serve.py --docker
   User → serve.py → SSH → Remote Docker → Container → MkDocs Server
   Local Files ←→ Mutagen Sync ←→ Container Files
   - Connects to Docker daemon on remote server
   - Bidirectional file synchronization with Mutagen
   - Local and secure access through Mutagen port forwarding feature
   - Secure connection via SSH (Recommended method)

Mutagen Integration:
-------------------
Mutagen plays a critical role in Remote Docker mode:

1. Synchronization Setup:
   - Bidirectional sync between local dir ↔ remote container
   - Automatic change detection and synchronization with container on remote server
   - Smart fine-tuned ignore patterns (node_modules, .git, etc.)

2. Port Forwarding:
   - Container ports → Local ports
   - Local access to MkDocs server (localhost:8000)

3. Performance Optimization:
   - Delta synchronization (only changes)
   - Conflict resolution mechanism
   - Staging → Transitioning → Watching cycle

Main Functions:
--------------
- check_vendor_files(): Checks vendor dependencies (tools/vendor-builder)
- build_vendor_files(): Compiles missing vendor files (tools/vendor-builder)
- serve_docs(): Starts MkDocs server
- native_serve(): Runs in native mode
- docker_serve(): Runs in Docker mode (local or remote)

Environment Variables:
--------------------
- DOCKER_MODE: Running inside Docker container?
- DOCKER_HOST: Remote Docker daemon address (ssh://user@host)
- DOCKER_REMOTE_SERVE: Remote Docker serve mode active?

"""

import sys
import os
import json
import argparse
import platform

from lib import (
    load_config,
    check_mkdocs,
    check_node,
    check_docker_environment,
    VendorManager,
    print_banner,
    get_logger,
    init_logging,
    setup_mkdocs_logging
)

# Disable Python tracebacks for cleaner error messages
# noinspection DuplicatedCode
# Enable traceback in verbose mode
sys.tracebacklimit = 0 if '--verbose' not in sys.argv and '-v' not in sys.argv else None

def check_vendor_files():
    """Check if all required vendor files exist"""
    config_data = load_config()
    vendor_manager = VendorManager(config_data)
    logger_ = get_logger(__name__)
    
    if not vendor_manager.vendor_dir.exists():
        logger_.warning("Vendor directory not found")
        return False
    
    if not vendor_manager.dependencies_file.exists():
        logger_.warning(f"Dependencies file not found: {vendor_manager.dependencies_file}")
        return False
    
    # Parse dependencies.json to get required files
    try:
        with open(vendor_manager.dependencies_file, 'r', encoding='utf-8') as deps_file:
            deps = json.load(deps_file)
            
        missing_files = []
        for dep in deps.get('dependencies', []):
            expected_filename = vendor_manager.get_expected_filename(dep)
            
            file_path = vendor_manager.vendor_dir / expected_filename
            if not file_path.exists():
                missing_files.append(expected_filename)
                logger_.warning(f"Missing vendor file: {expected_filename}")
        
        # Also check for webfonts directory (special case for Font Awesome)
        webfonts_dir = vendor_manager.vendor_dir / 'webfonts'
        if not webfonts_dir.exists():
            logger_.warning("Missing vendor directory: webfonts")
            return False
        
        return len(missing_files) == 0
            
    except json.JSONDecodeError as json_err:
        logger_.error(f"Error parsing dependencies.json: {json_err}")
        return False
    except Exception as err:
        logger_.error(f"Error reading dependencies: {err}")
        return False

def build_vendor_files():
    """Build vendor dependencies"""
    config_data = load_config()
    vendor_manager = VendorManager(config_data)
    logger_ = get_logger(__name__)
    
    logger_.info("Building vendor dependencies...")
    
    if not vendor_manager.vendor_builder_dir.exists():
        logger_.error(f"Error: {vendor_manager.vendor_builder_dir} directory not found!")
        return False

    # Build using VendorManager
    if vendor_manager.build_dependencies():
        logger_.info("Vendor files built successfully!")
        return True
    else:
        logger_.error("Failed to build vendor files")
        return False

def serve_docs():
    """Start MkDocs development server"""
    config_data = load_config()
    port = config_data.get('serve', {}).get('port', 8000)
    host = config_data.get('serve', {}).get('host', 'localhost')
    logger_ = get_logger(__name__)
    
    # Check if running in Docker and not using remote Docker
    if os.environ.get('DOCKER_MODE') == '1' and not os.environ.get('DOCKER_REMOTE_SERVE'):
        # In local Docker, bind to 0.0.0.0 for external access
        host = '0.0.0.0'

    dev_addr = f'{host}:{port}'
    # noinspection HttpUrlsUsage
    logger_.info(f"Serving documentation at http://{host}:{port}")
    logger_.info("Press Ctrl+C to stop")
    
    try:
        # Import MkDocs modules
        from mkdocs.commands.serve import serve
        
        # Set up MkDocs logging integration
        setup_mkdocs_logging()
        
        # Start the development server with config file path
        serve(config_file='mkdocs.yml', dev_addr=dev_addr, livereload=True)
        
    except KeyboardInterrupt:
        logger_.info("Stopping server...")
        sys.exit(0)
    except ImportError as import_err:
        logger_.error(f"Failed to import MkDocs: {import_err}")
        logger_.error("Please ensure MkDocs is installed: pip install mkdocs")
        sys.exit(1)
    except Exception as mkdocs_err:
        logger_.error(f"Error running MkDocs: {mkdocs_err}")
        sys.exit(1)

def native_serve():
    """Run serve in native mode"""
    config_data = load_config()
    logger_ = get_logger(__name__)
    
    # Check if MkDocs is installed
    if not check_mkdocs():
        logger_.critical("MkDocs is not installed. Please install MkDocs to run the development server.")
        logger_.critical("Install it with: pip install mkdocs")
        sys.exit(1)
    
    # Check and build vendor files if necessary
    if config_data.get('serve', {}).get('check_vendor_dependencies', True):
        logger_.info("Checking vendor dependencies...")
        if not check_vendor_files():
            # Check if Node.js is installed for building vendor files
            if not check_node():
                logger_.critical("Node.js is not installed. Please install Node.js to build vendor files.")
                logger_.critical("Visit https://nodejs.org/ for installation instructions.")
                logger_.warning("Some features (charts, asciinema) may not work properly without vendor files.")
                sys.exit(1)
            elif not build_vendor_files():
                logger_.warning("Warning: Could not build vendor files.")
                logger_.warning("Some features (charts, asciinema) may not work properly.")
                sys.exit(1)
        else:
            logger_.info("All vendor files are present")
    
    # Start development server
    serve_docs()

# noinspection DuplicatedCode
def docker_serve():
    """Run serve in Docker mode"""
    logger_ = get_logger(__name__)
    
    # Check Docker environment (local or remote)
    docker_env = check_docker_environment()
    
    if not docker_env['available']:
        logger_.critical(docker_env['error'])
        
        if docker_env['type'] == 'remote':
            logger_.critical(f"Remote Docker host: {docker_env['docker_host']}")
            logger_.critical("Ensure the remote Docker daemon is accessible")
        else:
            logger_.critical("Visit https://docs.docker.com/get-docker/ for installation instructions.")
        
        sys.exit(1)
    
    # Log connection type
    if docker_env['type'] == 'remote':
        logger_.info(f"Using remote Docker daemon at {docker_env['docker_host']}")
    
    # Import DockerManager only if Docker is available
    from lib import DockerManager
    
    config_data = load_config()
    docker_manager = DockerManager(config_data)
    
    # Connect to Docker
    if not docker_manager.connect():
        logger_.critical("Cannot proceed without Docker")
        sys.exit(1)
    
    # Ensure Docker image exists
    if not docker_manager.ensure_image():
        logger_.critical("Failed to prepare Docker image")
        sys.exit(1)
    
    # Run serve in container
    try:
        port = config_data.get('serve', {}).get('port', 8000)
        docker_manager.run_serve(port=port)
    except KeyboardInterrupt:
        logger_.info("Stopping container...")
    finally:
        # Cleanup
        docker_manager.cleanup()

# noinspection DuplicatedCode
def main():
    """Main entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Phantom Documentation Kit Development Server',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--docker',
        action='store_true',
        help='Run server in Docker container'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Reduce logging output'
    )
    
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    
    # Print banner first
    print_banner("serve")
    
    # Initialize logging after banner
    init_logging(config)
    
    # Apply verbosity settings
    logger_ = get_logger(__name__)
    if args.verbose:
        import os
        os.environ['PHANTOM_LOG_LEVEL'] = 'DEBUG'
        # Re-initialize logging with new level
        init_logging(config)
        logger_.debug("Verbose mode enabled")
    elif args.quiet:
        import os
        os.environ['PHANTOM_LOG_LEVEL'] = 'WARNING'
        # Re-initialize logging with new level
        init_logging(config)
    
    # Run in appropriate mode
    if args.docker:
        # Check if Windows
        if platform.system().lower() == 'windows':
            logger_.warning("Docker mode is not supported on Windows due to signal handling limitations")
            logger_.info("Please run without the --docker flag")
            sys.exit(1)
        else:
            logger_.info("Running in Docker mode")
            docker_serve()
    else:
        native_serve()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger = get_logger(__name__)
        logger.info("Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger = get_logger(__name__)
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)