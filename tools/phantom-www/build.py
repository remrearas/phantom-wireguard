#!/usr/bin/env python3
"""
Phantom WWW Build System
Converts markdown content to static HTML pages
"""

import argparse
import shutil
import sys
import logging
import yaml
from pathlib import Path
from textwrap import dedent

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

        WWW Build System - Static Site Generator
        Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
    """).strip()

    # Print banner without timestamp
    print(banner)
    print()


class PhantomBuilder:
    def __init__(self, src_dir, dist_dir, assets_dir):
        self.src_dir = Path(src_dir)
        self.dist_dir = Path(dist_dir)
        self.assets_dir = Path(assets_dir)

        # Initialize processors
        self.content_processor = ContentProcessor(self.src_dir / 'content')
        self.template_renderer = TemplateRenderer(self.src_dir / 'templates')
        self.asset_processor = AssetProcessor(self.assets_dir, env='prod')

    def build(self, language='en'):
        """Build for a specific language"""
        logger.info(f"Building {language.upper()} version")

        # Process markdown content
        logger.info("Processing markdown content")
        content = self.content_processor.process_all(language)

        # Render module cards and details
        logger.info("Rendering module templates")
        for module in content['modules']:
            module['card_html'] = self.template_renderer.render_module_card(module)
            module['detail_html'] = self.template_renderer.render_module_detail(module)

        # Render main template
        logger.info("Rendering main template")
        html = self.template_renderer.render('index.template.j2', {
            'lang': language,
            'env': 'prod',
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
        logger.info("Phantom WWW Build System")
        logger.info("Starting build process")

        for lang in config['languages']:
            try:
                self.build(lang)
            except Exception as e:
                logger.error(f"Error building {lang}: {e}")
                import traceback
                traceback.print_exc()
                continue

        # Copy assets
        logger.info("Copying assets to dist directory")
        self.asset_processor.copy_to_dist(self.dist_dir)

        logger.info("Build completed successfully")
        logger.info(f"Output directory: {self.dist_dir.absolute()}")

    def clean(self):
        """Clean dist directory"""
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
            logger.info(f"Cleaned {self.dist_dir}")


def main():
    # Display banner before anything else
    print_banner()

    # Help text
    epilog_text = dedent("""
        Examples:
          python build.py              # Build all languages for production
          python build.py --clean      # Clean before building
    """).strip()

    parser = argparse.ArgumentParser(
        description='Build Phantom WWW static site from markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog_text
    )

    parser.add_argument('--clean', action='store_true',
                       help='Clean dist directory before build')

    args = parser.parse_args()

    # Get project root
    project_root = Path(__file__).parent

    # Initialize builder
    builder = PhantomBuilder(
        src_dir=project_root / 'src',
        dist_dir=project_root / 'dist',
        assets_dir=project_root / 'src' / 'assets'
    )

    # Clean if requested
    if args.clean:
        builder.clean()

    # Build all languages
    builder.build_all_languages()


if __name__ == '__main__':
    main()