#!/usr/bin/env python3
"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>

TR: Phantom Documentation Kit Üretim Derleyici (build.py)
===================================================

Bu script, Phantom Documentation Kit projelerini production ortamına hazır bir şekilde, mkdocs ile derler.
Üç farklı modda çalışabilir: Native (yerel), Local Docker ve Remote Docker.
Her mod, farklı senaryolar ve gereksinimler için optimize edilmiştir.

mkdocs ile statik site oluşturma sürecininin arka tarafını otomatikleştirir ve kullanıma hazır çıktıları
farklı platform senaryolarında çalıştırma kolaylığı sağlar.

Çalışma Modları:
---------------

1. Native Mode (Local Mod):
   Komut: python build.py
   User → build.py → Vendor Build → MkDocs Build → Static HTML
   - Doğrudan yerel makinede çalışır
   - En hızlı derleme süresi
   - Python ve Node.js kurulumu gerektirir
   - Vendor dosyaları kontrolü ve otomatik derleme, optimizasyon

2. Local Docker Mode:
   Komut: python build.py --docker
   User → build.py → Docker Container → Build Process → Static HTML
   - Yerel Docker daemon kullanır
   - İzole edilmiş ortamda derleme
   - Tutarlı derleme ortamı garantisi
   - Dependency yönetimi kolaylığı
   - Volume mount ile dosya senkronizasyonu

3. Remote Docker Mode:
   Komut: DOCKER_HOST=ssh://user@server && python build.py --docker
   User → build.py → SSH → Remote Docker → Container → Build → Static HTML
   Local Files ←→ Mutagen Sync ←→ Container Files
   - Uzak sunucudaki Docker daemon'a bağlanır
   - Mutagen ile bidirectional (çift-yönlü) dosya senkronizasyonu
   - SSH üzerinden güvenli bağlantı
   - Büyük projeler için güçlü sunucu kaynaklarını kullanır
   - Derleme sonuçları Mutagen ile yerel makineye senkronize edilir

Mutagen Entegrasyonu:
-------------------
Remote Docker modunda Mutagen kritik rol oynar:

1. Senkronizasyon Kurulumu:
   - Yerel proje dizini ↔ Uzak container arasında bidirectional sync
   - Akıllı ignore pattern'ları (node_modules, outputs/, .git vb.)

2. Derleme Sürecinde:
   - Kaynak dosyalar otomatik olarak container'a senkronize edilir
   - Derleme işlemi uzak sunucuda gerçekleşir
   - Sonuçlar (outputs/) yerel makineye .tar.gz arşivi olarak geri senkronize edilir

Derleme Akışı:
-------------

1. Ön Hazırlık:
   - Vendor bağımlılıklarının kontrolü
   - Eksik paketlerin otomatik indirilmesi
   - JavaScript/CSS optimizasyonu (minifikasyon)

2. Temizlik İşlemleri:
   - Önceki derleme çıktılarının temizlenmesi
   - outputs/ dizininin hazırlanması

3. MkDocs Derlemesi:
   - Markdown → HTML dönüşümü
   - Tema uygulaması ve özelleştirmeler
   - Statik asset'lerin kopyalanması
   - Plugin işlemleri (search index, sitemap vb.)

4. Çıktı:
   - Üretim ortamına hazır paket (Native Local ve Docker Local modundayken www/ dizini içerisinde, Remote Docker
                                  modundayken .tar.gz arşivi olarak.)

Ana Fonksiyonlar:
----------------
- check_vendor_dependencies(): Vendor dosyalarını kontrol eder ve gerekirse derler
- clean_site_directory(): Önceki derleme çıktılarını temizler
- build_documentation(): MkDocs ile dokümantasyonu derler
- show_build_success(): Başarılı derleme sonrası bilgileri gösterir
- native_build(): Yerel modda derleme yapar
- docker_build(): Docker modunda derleme yapar (local veya remote)

Konfigürasyon (config.json):
---------------------------
{
  "build": {
    "check_vendor_dependencies": true,  // Vendor kontrolü yapılsın mı?
    "clean_before_build": true         // Derlemeden önce temizlik yapılsın mı?
  },
  "paths": {
    "output_dir": "outputs/site"       // Derleme çıktı dizini
  }
}

========================================================
EN: Phantom Documentation Kit Production Builder (build.py)
=======================================================

This script compiles Phantom Documentation Kit projects into production-ready format with mkdocs.
It can operate in three different modes: Native (local), Local Docker, and Remote Docker.
Each mode is optimized for different scenarios and requirements.

It automates the backend of the static site generation process with mkdocs and provides easy execution
of ready-to-use outputs across different platform scenarios.

Operating Modes:
---------------

1. Native Mode (Local Mode):
   Command: python build.py
   User → build.py → Vendor Build → MkDocs Build → Static HTML
   - Runs directly on local machine
   - Fastest build time
   - Requires Python and Node.js installation
   - Automatic vendor dependency checking and optimization

2. Local Docker Mode:
   Command: python build.py --docker
   User → build.py → Docker Container → Build Process → Static HTML
   - Uses local Docker daemon
   - Build in isolated environment
   - Guaranteed consistent build environment
   - Easy dependency management
   - File synchronization via volume mounts

3. Remote Docker Mode:
   Command: DOCKER_HOST=ssh://user@server && python build.py --docker
   User → build.py → SSH → Remote Docker → Container → Build → Static HTML
   Local Files ←→ Mutagen Sync ←→ Container Files
   - Connects to Docker daemon on remote server
   - Bidirectional file synchronization with Mutagen
   - Secure connection via SSH
   - Utilizes powerful server resources for large projects
   - Build results synchronized back to local machine via Mutagen

Mutagen Integration:
-------------------
Mutagen plays a critical role in Remote Docker mode:

1. Synchronization Setup:
   - Bidirectional sync between local project dir ↔ remote container
   - Smart ignore patterns (node_modules, outputs/, .git, etc.)

2. During Build Process:
   - Source files automatically synced to container
   - Build process executes on remote server
   - Results (outputs/) synced back to local machine as .tar.gz archive

Build Flow:
-----------

1. Preparation:
   - Check vendor dependencies
   - Automatic download of missing packages
   - JavaScript/CSS optimization (minification)

2. Cleanup Operations:
   - Clean previous build outputs
   - Prepare outputs/ directory

3. MkDocs Build:
   - Markdown → HTML conversion
   - Theme application and customizations
   - Copy static assets
   - Plugin processing (search index, sitemap, etc.)

4. Output:
   - Production-ready package (in www/ directory for Native Local and Docker Local modes, as .tar.gz archive
                               for Remote Docker mode)

Main Functions:
--------------
- check_vendor_dependencies(): Checks vendor files and builds if needed
- clean_site_directory(): Cleans previous build outputs
- build_documentation(): Builds documentation with MkDocs
- show_build_success(): Shows information after successful build
- native_build(): Builds in native mode
- docker_build(): Builds in Docker mode (local or remote)

Configuration (config.json):
---------------------------
{
  "build": {
    "check_vendor_dependencies": true,  // Check vendor dependencies?
    "clean_before_build": true         // Clean before build?
  },
  "paths": {
    "output_dir": "outputs/site"       // Build output directory
  }
}

"""

import sys
import shutil
import argparse
import platform
from pathlib import Path

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
sys.tracebacklimit = 0

def check_vendor_dependencies():
    """Check and build vendor dependencies if needed"""
    config_data = load_config()
    logger_ = get_logger(__name__)
    vendor_manager = VendorManager(config_data)
    
    if not vendor_manager.vendor_builder_dir.exists():
        return True  # No vendor builder, skip
    
    logger_.info("Checking vendor dependencies...")
    
    vendor_files_exist = vendor_manager.check_dependencies()
    
    if not vendor_files_exist:
        logger_.info("Building vendor dependencies...")
        
        if vendor_manager.build_dependencies():
            if vendor_manager.check_dependencies():
                logger_.info("Vendor files built successfully")
            else:
                logger_.error("Failed to build vendor files")
                return False
        else:
            logger_.error("Failed to build vendor files")
            logger_.warning("   Continuing without vendor files...")
            return True
    else:
        logger_.info("Vendor files are up to date")
    
    return True

def clean_site_directory():
    """Clean previous build"""
    config_data = load_config()
    logger_ = get_logger(__name__)
    site_dir = Path(config_data['paths']['output_dir'])
    if site_dir.exists():
        logger_.info("Cleaning previous build...")
        try:
            shutil.rmtree(site_dir)
            logger_.info("Previous build cleaned")
        except Exception as clean_err:
            logger_.error(f"Failed to clean site directory: {clean_err}", exc_info=False)
            return False
    return True

def build_documentation():
    """Build the documentation"""
    config_data = load_config()
    logger_ = get_logger(__name__)
    logger_.info("Building documentation...")
    
    # Create outputs directory if it doesn't exist
    outputs_dir = Path("outputs")
    if not outputs_dir.exists():
        outputs_dir.mkdir(parents=True)
    
    try:
        # Import MkDocs modules
        from mkdocs.commands.build import build
        from mkdocs.config import load_config as mkdocs_load_config
        
        # Set up MkDocs logging integration
        setup_mkdocs_logging()
        
        # Load MkDocs configuration
        mkdocs_config = mkdocs_load_config('mkdocs.yml')
        
        # Override site_dir with our config
        mkdocs_config.site_dir = config_data['paths']['output_dir']
        
        # Build the documentation
        build(mkdocs_config)
        
        return True
        
    except ImportError as import_err:
        logger_.error(f"Failed to import MkDocs: {import_err}")
        logger_.error("Please ensure MkDocs is installed: pip install mkdocs")
        return False
    except Exception as build_err:
        logger_.error(f"Build failed: {build_err}")
        return False

def show_build_success():
    """Show success message with next steps"""
    config_data = load_config()
    logger_ = get_logger(__name__)
    logger_.info("Documentation built successfully!")
    logger_.info(f"Output directory: ./{config_data['paths']['output_dir']}")
    logger_.info("To preview locally, run:")
    
    port = config_data.get('serve', {}).get('port', 8000)
    preview_cmd = f"python -m http.server {port} --directory {config_data['paths']['output_dir']}"
    logger_.info(f"   {preview_cmd}")

def native_build():
    """Run build in native mode"""
    config_data = load_config()
    logger_ = get_logger(__name__)
    
    # Check if MkDocs is installed
    if not check_mkdocs():
        logger_.critical("MkDocs is not installed. Please install MkDocs to build documentation.")
        logger_.critical("Install it with: pip install mkdocs")
        sys.exit(1)
    
    # Build vendor dependencies if needed
    if config_data['build'].get('check_vendor_dependencies', True):
        vendor_manager = VendorManager(config_data)
        vendor_files_exist = vendor_manager.check_dependencies()
        
        if not vendor_files_exist:
            # Check if Node.js is installed for building vendor files
            if not check_node():
                logger_.critical("Node.js is not installed. Please install Node.js to build vendor files.")
                logger_.critical("Visit https://nodejs.org/ for installation instructions.")
                logger_.warning("Cannot build vendor files without Node.js.")
                logger_.warning("Continuing without vendor files...")
            elif not check_vendor_dependencies():
                logger_.warning("Continuing without vendor files...")
    
    # Clean previous build
    if config_data['build'].get('clean_before_build', True) and not clean_site_directory():
        logger_.warning("Warning: Could not clean previous build")
    
    # Build documentation
    if build_documentation():
        show_build_success()
    else:
        logger_.error("Build failed! Please check the errors above.")
        sys.exit(1)

def docker_build():
    """Run build in Docker mode"""
    # noinspection DuplicatedCode
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
    
    # Run build in container
    if docker_manager.run_build():
        show_build_success()
    else:
        logger_.error("Docker build failed! Please check the errors above.")
        sys.exit(1)
    
    # Cleanup
    docker_manager.cleanup()

# noinspection DuplicatedCode
def main():
    """Main entry point"""
    # Parse command line arguments

    parser = argparse.ArgumentParser(
        description='Phantom Documentation Kit Build Script',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--docker',
        action='store_true',
        help='Run build in Docker container'
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
    print_banner("build")
    
    # Initialize logging after banner
    init_logging(config)
    
    # Apply verbosity settings
    logger_ = get_logger(__name__)
    if args.verbose:
        import os
        os.environ['PHANTOM_LOG_LEVEL'] = 'DEBUG'
        # Re-initialize logging with new level
        init_logging(config)
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
            docker_build()
    else:
        native_build()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger = get_logger(__name__)
        logger.info("Build cancelled!")
        sys.exit(0)
    except Exception as e:
        logger = get_logger(__name__)
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)