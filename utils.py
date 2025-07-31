import os
import difflib
from markupsafe import Markup

def get_file_extension(file_path):
    """Get file extension for syntax highlighting"""
    _, ext = os.path.splitext(file_path)
    return ext.lower()

def is_text_file(file_path):
    """Check if file is a text file"""
    text_extensions = {
        '.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.yml', '.yaml',
        '.ini', '.cfg', '.conf', '.sh', '.sql', '.csv', '.log', '.rst', '.tex'
    }
    _, ext = os.path.splitext(file_path)
    return ext.lower() in text_extensions

def format_diff(original, modified):
    """Format diff for HTML display"""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile='Original',
        tofile='Modified',
        lineterm=''
    )
    
    html_lines = []
    for line in diff:
        if line.startswith('+++') or line.startswith('---'):
            html_lines.append(f'<div class="diff-header">{line}</div>')
        elif line.startswith('@@'):
            html_lines.append(f'<div class="diff-range">{line}</div>')
        elif line.startswith('+'):
            html_lines.append(f'<div class="diff-added">{line}</div>')
        elif line.startswith('-'):
            html_lines.append(f'<div class="diff-removed">{line}</div>')
        else:
            html_lines.append(f'<div class="diff-context">{line}</div>')
    
    return Markup('\n'.join(html_lines))

def get_language_mode(file_path):
    """Get CodeMirror language mode based on file extension"""
    extension_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.html': 'htmlmixed',
        '.css': 'css',
        '.json': 'javascript',
        '.xml': 'xml',
        '.md': 'markdown',
        '.sql': 'sql',
        '.sh': 'shell',
        '.yaml': 'yaml',
        '.yml': 'yaml'
    }
    
    _, ext = os.path.splitext(file_path)
    return extension_map.get(ext.lower(), 'text')
