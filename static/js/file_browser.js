// File browser functionality
class FileBrowser {
    constructor() {
        this.expandedFolders = new Set();
        this.searchFilter = '';
    }
    
    init() {
        this.setupEventListeners();
        this.restoreExpandedState();
    }
    
    setupEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('file-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchFilter = e.target.value.toLowerCase();
                this.filterFiles();
            });
        }
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'f':
                        e.preventDefault();
                        this.focusSearch();
                        break;
                    case 'n':
                        e.preventDefault();
                        this.showNewFileModal();
                        break;
                }
            }
        });
    }
    
    toggleFolder(folderId) {
        const content = document.getElementById('content-' + folderId);
        const icon = document.getElementById('icon-' + folderId);
        const toggleIcon = document.getElementById('toggle-' + folderId);
        
        if (!content || !icon || !toggleIcon) {
            console.error('Missing elements for folder:', folderId);
            return;
        }
        
        if (content.style.display === 'none' || content.style.display === '') {
            // Expand folder
            content.style.display = 'block';
            icon.classList.remove('fa-folder');
            icon.classList.add('fa-folder-open');
            toggleIcon.classList.remove('fa-chevron-right');
            toggleIcon.classList.add('fa-chevron-down');
            this.expandedFolders.add(folderId);
        } else {
            // Collapse folder
            content.style.display = 'none';
            icon.classList.remove('fa-folder-open');
            icon.classList.add('fa-folder');
            toggleIcon.classList.remove('fa-chevron-down');
            toggleIcon.classList.add('fa-chevron-right');
            this.expandedFolders.delete(folderId);
        }
        
        this.saveExpandedState();
    }
    
    saveExpandedState() {
        localStorage.setItem('wiki_expanded_folders', JSON.stringify([...this.expandedFolders]));
    }
    
    restoreExpandedState() {
        const saved = localStorage.getItem('wiki_expanded_folders');
        if (saved) {
            this.expandedFolders = new Set(JSON.parse(saved));
            
            // Restore expanded state
            this.expandedFolders.forEach(folderId => {
                this.toggleFolder(folderId);
            });
        }
    }
    
    filterFiles() {
        const items = document.querySelectorAll('.file-tree-item');
        
        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            const matches = !this.searchFilter || text.includes(this.searchFilter);
            item.style.display = matches ? 'block' : 'none';
            
            // Show parent folders if child matches
            if (matches) {
                let parent = item.closest('.folder-contents');
                while (parent) {
                    parent.style.display = 'block';
                    const header = parent.previousElementSibling;
                    if (header && header.classList.contains('folder-header')) {
                        const icon = header.querySelector('.toggle-icon');
                        const folderIcon = header.querySelector('.folder-icon');
                        icon.classList.remove('fa-chevron-right');
                        icon.classList.add('fa-chevron-down');
                        folderIcon.classList.remove('fa-folder');
                        folderIcon.classList.add('fa-folder-open');
                    }
                    parent = parent.closest('.folder-contents');
                }
            }
        });
    }
    
    focusSearch() {
        const searchInput = document.getElementById('file-search');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }
    
    showNewFileModal() {
        // Placeholder for new file creation functionality
        console.log('New file modal would open here');
    }
    
    getFileIcon(fileName) {
        const extension = fileName.split('.').pop().toLowerCase();
        const iconMap = {
            'md': 'fab fa-markdown',
            'py': 'fab fa-python',
            'js': 'fab fa-js',
            'html': 'fab fa-html5',
            'css': 'fab fa-css3-alt',
            'json': 'fas fa-code',
            'xml': 'fas fa-code',
            'yml': 'fas fa-cog',
            'yaml': 'fas fa-cog',
            'txt': 'fas fa-file-alt',
            'sql': 'fas fa-database',
            'sh': 'fas fa-terminal'
        };
        
        return iconMap[extension] || 'fas fa-file';
    }
}

// Initialize file browser when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const fileBrowser = new FileBrowser();
    fileBrowser.init();
    
    // Make toggleFolder globally accessible
    window.toggleFolder = (folderId) => fileBrowser.toggleFolder(folderId);
});
