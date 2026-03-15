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

// Code block language badges
document.addEventListener('DOMContentLoaded', function() {
    // Language to badge mapping
    const languageBadges = {
        'bash': { text: 'BASH', color: 'var(--phantom-accent)' },
        'shell': { text: 'SHELL', color: '#4eaa25' },
        'sh': { text: 'SHELL', color: '#4eaa25' },
        'python': { text: 'PYTHON', color: '#1976d2' },
        'py': { text: 'PYTHON', color: '#1976d2' },
        'python3': { text: 'PYTHON', color: '#1976d2' },
        'yaml': { text: 'YAML', color: '#7b1fa2' },
        'yml': { text: 'YAML', color: '#7b1fa2' },
        'json': { text: 'JSON', color: '#f57c00' },
        'text': { text: 'OUTPUT', color: 'var(--phantom-info)' },
        'output': { text: 'OUTPUT', color: 'var(--phantom-info)' },
        'plaintext': { text: 'TEXT', color: '#6c757d' },
        'javascript': { text: 'JAVASCRIPT', color: '#f7df1e', textColor: '#000' },
        'js': { text: 'JAVASCRIPT', color: '#f7df1e', textColor: '#000' },
        'typescript': { text: 'TYPESCRIPT', color: '#3178c6' },
        'ts': { text: 'TYPESCRIPT', color: '#3178c6' },
        'html': { text: 'HTML', color: '#e34c26' },
        'css': { text: 'CSS', color: '#1572b6' },
        'dockerfile': { text: 'DOCKERFILE', color: '#2496ed' },
        'docker': { text: 'DOCKER', color: '#2496ed' },
        'sql': { text: 'SQL', color: '#336791' },
        'go': { text: 'GO', color: '#00add8' },
        'rust': { text: 'RUST', color: '#dea584' },
        'java': { text: 'JAVA', color: '#007396' },
        'c': { text: 'C', color: '#555555' },
        'cpp': { text: 'C++', color: '#f34b7d' },
        'csharp': { text: 'C#', color: '#178600' },
        'php': { text: 'PHP', color: '#777bb4' },
        'ruby': { text: 'RUBY', color: '#cc342d' },
        'swift': { text: 'SWIFT', color: '#fa7343' },
        'kotlin': { text: 'KOTLIN', color: '#7f52ff' },
        'r': { text: 'R', color: '#276dc3' },
        'matlab': { text: 'MATLAB', color: '#e16737' },
        'perl': { text: 'PERL', color: '#39457e' },
        'lua': { text: 'LUA', color: '#000080' },
        'markdown': { text: 'MARKDOWN', color: '#083fa1' },
        'md': { text: 'MARKDOWN', color: '#083fa1' },
        'xml': { text: 'XML', color: '#e34c26' },
        'toml': { text: 'TOML', color: '#9c4121' },
        'ini': { text: 'INI', color: '#d1dbe0', textColor: '#000' },
        'conf': { text: 'CONFIG', color: '#6d8086' },
        'nginx': { text: 'NGINX', color: '#009639' },
        'apache': { text: 'APACHE', color: '#d12127' }
    };

    // Function to apply badges
    function applyBadges() {
        // Find all pre elements in the typeset
        const preElements = document.querySelectorAll('.md-typeset pre');
        
        preElements.forEach((pre) => {
            // Skip if already has a data-terminal-type attribute
            if (pre.hasAttribute('data-terminal-type')) {
                return;
            }
            
            let language = null;
            const parent = pre.parentElement;
            
            // Method 1: Check if parent is a div.highlight with language class
            if (parent && parent.classList.contains('highlight')) {
                const parentClasses = Array.from(parent.classList);
                
                for (const cls of parentClasses) {
                    if (cls.startsWith('language-')) {
                        language = cls.replace('language-', '');
                        break;
                    }
                }
            }
            
            // Method 2: Check the code element inside pre
            if (!language) {
                const code = pre.querySelector('code');
                if (code) {
                    const codeClasses = Array.from(code.classList);
                    
                    for (const cls of codeClasses) {
                        if (cls.startsWith('language-')) {
                            language = cls.replace('language-', '');
                            break;
                        }
                    }
                }
            }
            
            // Method 3: Check data attributes on the parent highlight div
            if (!language && parent && parent.dataset.lang) {
                language = parent.dataset.lang;
            }
            
            if (language && languageBadges[language]) {
                const badge = languageBadges[language];
                
                // Set data attribute for CSS
                pre.setAttribute('data-terminal-type', badge.text.toLowerCase());
                
                // Create style for this specific badge if not exists
                const styleId = `badge-style-${badge.text.toLowerCase()}`;
                if (!document.getElementById(styleId)) {
                    const style = document.createElement('style');
                    style.id = styleId;
                    style.textContent = `
                        .md-typeset pre[data-terminal-type="${badge.text.toLowerCase()}"]::before {
                            content: "${badge.text}" !important;
                            background-color: ${badge.color} !important;
                            ${badge.textColor ? `color: ${badge.textColor} !important;` : ''}
                        }
                    `;
                    document.head.appendChild(style);
                }
            } else if (language) {
                // If language is detected but not in our list, use the language name
                pre.setAttribute('data-terminal-type', language);
                
                // Create a generic code badge
                const styleId = `badge-style-${language}`;
                if (!document.getElementById(styleId)) {
                    const style = document.createElement('style');
                    style.id = styleId;
                    style.textContent = `
                        .md-typeset pre[data-terminal-type="${language}"]::before {
                            content: "${language.toUpperCase()}" !important;
                            background-color: var(--phantom-accent) !important;
                        }
                    `;
                    document.head.appendChild(style);
                }
            }
        });
    }

    // Apply badges immediately and after a delay
    applyBadges();
    setTimeout(applyBadges, 200);
    setTimeout(applyBadges, 500);
    
    // Also apply on any dynamic content changes
    // noinspection JSUnusedLocalSymbols
    const observer = new MutationObserver(function(mutations) {
        applyBadges();
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
});