"""
Content processor for markdown files
"""

import frontmatter
import markdown
import re
from pathlib import Path


class ContentProcessor:
    def __init__(self, content_dir):
        self.content_dir = Path(content_dir)
        self.md = markdown.Markdown(extensions=[
            'fenced_code',
            'tables',
            'attr_list'
        ])

    def process_all(self, language='en'):
        """Process all content for a specific language"""
        return {
            'hero': self.process_hero(language),
            'install': self.process_install(language),
            'modules': self.process_modules(language),
            'features': self.process_features(language),
            'wizard': self.process_wizard(language),
            'donate': self.process_donate(language),
            'footer': self.process_footer(language)
        }

    def process_hero(self, language):
        """Process hero section markdown"""
        hero_file = self.content_dir / 'landing' / language / 'hero.md'

        with open(hero_file, encoding='utf-8') as f:
            post = frontmatter.load(f)

        # Extract h1 for title
        title_match = re.search(r'^#\s+(.+)$', post.content, re.MULTILINE)
        title = title_match.group(1) if title_match else post.metadata['title']

        # Extract remaining text as tagline
        tagline = re.sub(r'^#\s+.+$', '', post.content, flags=re.MULTILINE).strip()

        return {
            'logo': post.metadata['logo'],
            'logo_alt': post.metadata['logo_alt'],
            'title': title,
            'tagline': tagline
        }

    def process_install(self, language):
        """Process install section markdown"""
        install_file = self.content_dir / 'landing' / language / 'install.md'

        with open(install_file, encoding='utf-8') as f:
            post = frontmatter.load(f)

        # Extract h2 title
        title_match = re.search(r'^##\s+(.+)$', post.content, re.MULTILINE)
        title = title_match.group(1) if title_match else post.metadata['title']

        # Extract code block
        code_match = re.search(r'```(\w+)?\n(.+?)\n```', post.content, re.DOTALL)
        if code_match:
            lang = code_match.group(1) or post.metadata.get('language', 'bash')
            command = code_match.group(2).strip()
        else:
            lang = post.metadata.get('language', 'bash')
            command = post.metadata['command']

        return {
            'title': title,
            'command': command,
            'language': lang
        }

    def process_modules(self, language):
        """Process all module markdown files"""
        modules_dir = self.content_dir / 'modules' / language
        modules = []

        for md_file in sorted(modules_dir.glob('*.md')):
            with open(md_file, encoding='utf-8') as f:
                post = frontmatter.load(f)

            # Reset markdown converter for each file
            self.md.reset()

            # Convert markdown to HTML
            content_html = self.md.convert(post.content)

            modules.append({
                'id': post.metadata.get('id', md_file.stem),
                'label': post.metadata.get('label') or post.metadata['title'],
                'mini_desc': post.metadata.get('mini_desc') or post.metadata.get('subtitle', ''),
                'title': post.metadata['title'],
                'subtitle': post.metadata.get('subtitle', ''),
                'icon': post.metadata['icon'],
                'order': post.metadata.get('order', 999),
                'content_html': content_html,
                'metadata': post.metadata
            })

        return sorted(modules, key=lambda x: x['order'])

    def process_features(self, language):
        """Process feature slider markdown"""
        features_file = self.content_dir / 'features' / language / 'features.md'

        with open(features_file, encoding='utf-8') as f:
            post = frontmatter.load(f)

        # Split slides by horizontal rule
        slides_raw = post.content.split('\n---\n')
        slides = []

        for i, slide_content in enumerate(slides_raw):
            # Parse each slide
            title_match = re.search(r'^##\s+(.+)$', slide_content, re.MULTILINE)
            icon_match = re.search(r'\*\*icon:\*\*\s+(\w+)', slide_content)

            # Remove metadata lines and get description
            description = re.sub(r'^##\s+.+$', '', slide_content, flags=re.MULTILINE)
            description = re.sub(r'\*\*icon:\*\*\s+\w+', '', description).strip()

            slides.append({
                'title': title_match.group(1) if title_match else post.metadata.get('default_title', ''),
                'icon': icon_match.group(1) if icon_match else post.metadata.get('default_icon'),
                'description': description,
                'order': i
            })

        return {
            'slides': slides,
            'auto_rotate': post.metadata.get('auto_rotate', True),
            'rotation_interval': post.metadata.get('rotation_interval', 5000)
        }

    def process_donate(self, language):
        """Process donate modal markdown"""
        donate_file = self.content_dir / 'landing' / language / 'donate.md'

        with open(donate_file, encoding='utf-8') as f:
            post = frontmatter.load(f)

        return {
            'title': post.metadata['title'],
            'description': post.content.strip(),
            'bitcoin': post.metadata['bitcoin'],
            'monero': post.metadata['monero']
        }

    def process_wizard(self, language):
        """Process wizard section markdown"""
        wizard_file = self.content_dir / 'landing' / language / 'wizard.md'

        with open(wizard_file, encoding='utf-8') as f:
            post = frontmatter.load(f)

        return {
            'title': post.metadata['title'],
            'icon': post.metadata.get('icon', 'rocket'),
            'features': post.metadata.get('features', []),
            'mainnet': post.metadata.get('mainnet', {}),
            'onion': post.metadata.get('onion', {})
        }

    def process_footer(self, language):
        """Process footer markdown"""
        footer_file = self.content_dir / 'landing' / language / 'footer.md'

        with open(footer_file, encoding='utf-8') as f:
            post = frontmatter.load(f)

        content_lines = [line.strip() for line in post.content.strip().split('\n') if line.strip()]

        return {
            'links': post.metadata.get('links', []),
            'copyright': content_lines[0] if content_lines else post.metadata.get('copyright', ''),
            'disclaimer': content_lines[1] if len(content_lines) > 1 else '',
            'trademark': content_lines[2] if len(content_lines) > 2 else post.metadata.get('trademark', '')
        }