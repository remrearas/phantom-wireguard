"""
Template renderer using Jinja2
"""

from textwrap import dedent
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from pathlib import Path


class TemplateRenderer:
    def __init__(self, templates_dir):
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Add custom filters - mark strings as safe HTML
        self.env.filters['safe'] = lambda x: Markup(x)

    def render(self, template_name, context):
        """Render a template with given context"""
        template = self.env.get_template(template_name)
        return template.render(**context)

    @staticmethod
    def render_module_card(module):
        """Render a single module card HTML"""
        label = module.get('label', module['title'])
        mini_desc = module.get('mini_desc', module['subtitle'])

        html = dedent(f'''
            <div class="module-card" data-module="{module['id']}">
                <div class="module-icon">
                    <svg class="phantom-icon">
                        <use href="assets/icons/sprite.svg#icon-{module['icon']}"></use>
                    </svg>
                </div>
                <div class="module-label">{label}</div>
                <div class="module-mini-desc">{mini_desc}</div>
            </div>
        ''').strip()

        return Markup(html)

    @staticmethod
    def render_module_detail(module):
        """Render module detail template content"""
        html = dedent(f'''
            <div class="module-detail">
                <div class="module-header">
                    <h2 class="module-title">{module['title']}</h2>
                    <p class="module-subtitle">{module['subtitle']}</p>
                </div>
                <div class="module-body">
                    <div class="module-description-container">
                        {module['content_html']}
                    </div>
                </div>
            </div>
        ''').strip()

        return Markup(html)