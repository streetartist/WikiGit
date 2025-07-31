// Editor-specific JavaScript functionality
class WikiEditor {
    constructor() {
        this.editor = null;
        this.previewContainer = null;
        this.isMarkdown = false;
    }
    
    init(fileExtension, content) {
        this.isMarkdown = fileExtension === '.md';
        this.initEditor(fileExtension, content);
        
        if (this.isMarkdown) {
            this.initPreview();
        }
    }
    
    initEditor(fileExtension, content) {
        const textarea = document.getElementById('editor');
        const mode = this.getCodeMirrorMode(fileExtension);
        
        this.editor = CodeMirror.fromTextArea(textarea, {
            lineNumbers: true,
            mode: mode,
            theme: 'material-darker',
            lineWrapping: true,
            autoCloseBrackets: true,
            matchBrackets: true,
            indentUnit: 4,
            tabSize: 4,
            indentWithTabs: false,
            extraKeys: {
                "Ctrl-S": () => this.showSaveOptions(),
                "Cmd-S": () => this.showSaveOptions()
            }
        });
        
        this.editor.setSize(null, "500px");
        this.editor.setValue(content);
        
        // Auto-save to localStorage every 30 seconds
        setInterval(() => this.autoSave(), 30000);
    }
    
    initPreview() {
        this.previewContainer = document.getElementById('markdown-preview');
        if (this.previewContainer) {
            this.updatePreview();
            this.editor.on('change', () => this.updatePreview());
        }
    }
    
    updatePreview() {
        if (!this.previewContainer || !window.marked) return;
        
        const content = this.editor.getValue();
        this.previewContainer.innerHTML = marked.parse(content);
    }
    
    getCodeMirrorMode(extension) {
        const modes = {
            '.py': 'python',
            '.js': 'javascript',
            '.html': 'htmlmixed',
            '.css': 'css',
            '.json': 'javascript',
            '.md': 'markdown',
            '.sql': 'sql',
            '.sh': 'shell',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.xml': 'xml'
        };
        return modes[extension] || 'text';
    }
    
    autoSave() {
        if (this.editor) {
            const content = this.editor.getValue();
            const filePath = document.querySelector('input[name="file_path"]').value;
            localStorage.setItem(`wiki_editor_${filePath}`, content);
        }
    }
    
    loadAutoSave() {
        const filePath = document.querySelector('input[name="file_path"]').value;
        const saved = localStorage.getItem(`wiki_editor_${filePath}`);
        
        if (saved && this.editor) {
            const current = this.editor.getValue();
            if (saved !== current) {
                if (confirm('Found auto-saved changes. Do you want to restore them?')) {
                    this.editor.setValue(saved);
                }
            }
        }
    }
    
    clearAutoSave() {
        const filePath = document.querySelector('input[name="file_path"]').value;
        localStorage.removeItem(`wiki_editor_${filePath}`);
    }
    
    getValue() {
        return this.editor ? this.editor.getValue() : '';
    }
    
    showSaveOptions() {
        // Focus on save options panel
        const savePanel = document.querySelector('.card:has([onclick*="saveFile"])');
        if (savePanel) {
            savePanel.scrollIntoView({ behavior: 'smooth', block: 'center' });
            savePanel.classList.add('border-primary');
            setTimeout(() => savePanel.classList.remove('border-primary'), 2000);
        }
    }
}

// Global editor instance
let wikiEditor = new WikiEditor();

// Export for use in other scripts
window.WikiEditor = WikiEditor;
window.wikiEditor = wikiEditor;
