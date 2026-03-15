"""
Asset processor and optimizer
"""

import shutil
import logging
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from config.yaml"""
    # Assume config.yaml is in project root (parent of builder/)
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class AssetProcessor:
    def __init__(self, assets_dir, env='prod'):
        self.assets_dir = Path(assets_dir)
        self.env = env
        self.global_config = load_config()
        self.config = self.global_config['environments'][env]

    def copy_to_dist(self, dist_dir):
        """Copy assets to dist directory"""
        dist_assets = Path(dist_dir) / 'assets'
        dist_dir = Path(dist_dir)

        # Remove existing assets if present
        if dist_assets.exists():
            shutil.rmtree(dist_assets)

        # Copy all assets
        shutil.copytree(self.assets_dir, dist_assets, dirs_exist_ok=True)

        logger.info(f"Copied assets to {dist_assets}")

        # Remove excluded files in production
        if self.env == 'prod' and 'exclude_from_prod' in self.global_config['build']:
            for exclude_path in self.global_config['build']['exclude_from_prod']:
                file_to_remove = dist_assets / exclude_path
                if file_to_remove.exists():
                    file_to_remove.unlink()
                    logger.info(f"Excluded from production: {exclude_path}")

        # Copy root files from config (e.g., manifest.json, robots.txt)
        for root_file in self.global_config['build']['root_files']:
            file_src = self.assets_dir / root_file
            if file_src.exists():
                file_dest = dist_dir / root_file
                shutil.copy2(file_src, file_dest)
                logger.info(f"Copied {root_file} to {file_dest}")

                # Remove from dist/assets/ to avoid duplication
                duplicate = dist_assets / root_file
                if duplicate.exists():
                    duplicate.unlink()
                    logger.info(f"Removed duplicate {root_file} from assets")

        # Copy root directories from config (e.g., wheel/)
        for root_dir in self.global_config['build'].get('root_dirs', []):
            dir_src = self.assets_dir / root_dir
            if dir_src.is_dir():
                dir_dest = dist_dir / root_dir
                if dir_dest.exists():
                    shutil.rmtree(dir_dest)
                shutil.copytree(dir_src, dir_dest)
                logger.info(f"Copied directory {root_dir}/ to {dir_dest}")

                # Remove from dist/assets/ to avoid duplication
                duplicate = dist_assets / root_dir
                if duplicate.exists():
                    shutil.rmtree(duplicate)
                    logger.info(f"Removed duplicate {root_dir}/ from assets")

        # Optional: Minify in production
        if self.config['minify_css']:
            self._minify_css(dist_assets)

        if self.config['minify_js']:
            self._minify_js(dist_assets)

    @staticmethod
    def _minify_css(assets_dir):
        """Minify CSS files"""
        try:
            import cssmin
            css_files = (assets_dir / 'css').glob('*.css')

            for css_file in css_files:
                with open(css_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                minified = cssmin.cssmin(content)

                with open(css_file, 'w', encoding='utf-8') as f:
                    f.write(minified)

            logger.info("Minified CSS files")
        except ImportError:
            logger.warning("cssmin not installed, skipping CSS minification")

    @staticmethod
    def _minify_js(assets_dir):
        """Minify JS files"""
        try:
            import rjsmin
            js_files = (assets_dir / 'js').glob('*.js')

            for js_file in js_files:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                minified = rjsmin.jsmin(content)

                with open(js_file, 'w', encoding='utf-8') as f:
                    f.write(minified)

            logger.info("Minified JS files")
        except ImportError:
            logger.warning("rjsmin not installed, skipping JS minification")