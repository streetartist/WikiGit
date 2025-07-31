import os
import time
import logging
import git
from github import Github
from models import SystemConfig

class GitHubService:
    def __init__(self, token=None):
        self.token = token or self._get_system_token()
        self.repo_name = self._get_repo_name()
        self.local_repo_path = 'local_repo'
        self.github = Github(self.token) if self.token else None
        
    def _get_system_token(self):
        config = SystemConfig.query.filter_by(key='github_token').first()
        return config.value if config else None
    
    def _get_repo_name(self):
        config = SystemConfig.query.filter_by(key='github_repo').first()
        return config.value if config else None
    
    def _ensure_local_repo(self):
        """Ensure local repository exists and is up to date"""
        if not self.token or not self.repo_name:
            raise Exception("GitHub token and repository must be configured")
        
        try:
            if not os.path.exists(self.local_repo_path):
                # Clone the repository
                repo_url = f"https://{self.token}@github.com/{self.repo_name}.git"
                git.Repo.clone_from(repo_url, self.local_repo_path)
                logging.info(f"Cloned repository {self.repo_name}")
            else:
                # Check if it's a valid git repository
                try:
                    repo = git.Repo(self.local_repo_path)
                    # Verify remote origin exists
                    if 'origin' not in [remote.name for remote in repo.remotes]:
                        raise Exception("No origin remote found in repository")
                    
                    # Pull latest changes
                    origin = repo.remotes.origin
                    origin.pull()
                    logging.info("Pulled latest changes from repository")
                except git.exc.InvalidGitRepositoryError:
                    # Remove invalid repo and re-clone
                    import shutil
                    shutil.rmtree(self.local_repo_path)
                    repo_url = f"https://{self.token}@github.com/{self.repo_name}.git"
                    git.Repo.clone_from(repo_url, self.local_repo_path)
                    logging.info(f"Re-cloned invalid repository {self.repo_name}")
                    
        except git.exc.GitCommandError as e:
            error_msg = f"Git command failed during repository setup: {e.stderr.strip() if e.stderr else str(e)}"
            logging.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Repository setup failed: {str(e)}"
            logging.error(error_msg)
            raise Exception(error_msg)
    
    def sync_repository(self):
        """Sync local repository with remote"""
        self._ensure_local_repo()
    
    def get_file_tree(self, path=""):
        """Get file tree structure"""
        try:
            # Try to ensure local repo is up to date if configuration exists
            if self.token and self.repo_name:
                self._ensure_local_repo()
        except Exception as e:
            logging.warning(f"Could not sync with GitHub: {e}")
        
        # Check if local repo exists at all
        if not os.path.exists(self.local_repo_path):
            return []
        
        full_path = os.path.join(self.local_repo_path, path)
        if not os.path.exists(full_path):
            return []
        
        items = []
        for item in os.listdir(full_path):
            if item.startswith('.'):
                continue
            
            item_path = os.path.join(path, item) if path else item
            full_item_path = os.path.join(self.local_repo_path, item_path)
            
            if os.path.isdir(full_item_path):
                items.append({
                    'name': item,
                    'path': item_path,
                    'type': 'directory',
                    'children': self.get_file_tree(item_path)
                })
            else:
                items.append({
                    'name': item,
                    'path': item_path,
                    'type': 'file'
                })
        
        return sorted(items, key=lambda x: (x['type'] != 'directory', x['name'].lower()))
    
    def get_file_content(self, file_path):
        """Get content of a file"""
        try:
            # Try to ensure local repo is up to date if configuration exists
            if self.token and self.repo_name:
                self._ensure_local_repo()
        except Exception as e:
            logging.warning(f"Could not sync with GitHub: {e}")
        
        full_path = os.path.join(self.local_repo_path, file_path)
        if not os.path.exists(full_path):
            return ""
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Handle binary files
            with open(full_path, 'rb') as f:
                return f.read().decode('utf-8', errors='ignore')
    
    def file_exists(self, file_path):
        """Check if file exists"""
        try:
            # Try to ensure local repo is up to date if configuration exists
            if self.token and self.repo_name:
                self._ensure_local_repo()
        except Exception as e:
            logging.warning(f"Could not sync with GitHub: {e}")
        
        full_path = os.path.join(self.local_repo_path, file_path)
        return os.path.exists(full_path)
    
    def commit_and_push(self, file_path, content, commit_message):
        """Commit changes and push to repository"""
        try:
            self._ensure_local_repo()
            
            # Clean the file path to ensure it's relative - more comprehensive cleaning
            clean_file_path = file_path
            path_prefixes = [
                '/home/runner/workspace/local_repo/',
                '/home/runner/workspace/local_repo',
                'local_repo/',
                'local_repo',
                '/workspace/local_repo/',
                '/workspace/local_repo'
            ]
            
            for prefix in path_prefixes:
                if clean_file_path.startswith(prefix):
                    clean_file_path = clean_file_path[len(prefix):]
                    break
            
            # Remove any remaining leading slashes
            clean_file_path = clean_file_path.lstrip('/')
            
            if not clean_file_path:
                raise Exception("Invalid file path - cannot be empty after cleaning")
            
            logging.info(f"Committing file - Original: {file_path}, Cleaned: {clean_file_path}")
            
            full_path = os.path.join(self.local_repo_path, clean_file_path)
            
            # Create directory if it doesn't exist
            dir_path = os.path.dirname(full_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            
            # Write content to file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Git operations using GitPython properly
            repo = git.Repo(self.local_repo_path)
            
            try:
                # Check if there are actually changes to commit
                if repo.is_dirty() or len(repo.untracked_files) > 0:
                    # Add the file to the index
                    repo.index.add([clean_file_path])
                    
                    # Commit the changes
                    repo.index.commit(commit_message)
                    
                    # Push to remote
                    origin = repo.remotes.origin
                    origin.push()
                    
                    logging.info(f"Successfully committed and pushed changes to {clean_file_path}")
                else:
                    logging.info(f"No changes detected for {clean_file_path}")
                    
            except git.exc.GitCommandError as git_error:
                error_msg = f"Git command failed: {git_error.stderr.strip() if git_error.stderr else str(git_error)}"
                logging.error(f"Git error for {clean_file_path}: {error_msg}")
                raise Exception(error_msg)
            except Exception as git_error:
                error_msg = f"Git operation error: {str(git_error)}"
                logging.error(f"General git error for {clean_file_path}: {error_msg}")
                raise Exception(error_msg)
                
        except Exception as e:
            error_msg = f"Git operation failed for {file_path}: {str(e)}"
            logging.error(error_msg)
            raise Exception(error_msg)
    
    def create_pull_request(self, file_path, content, title, description=""):
        """Create a pull request with the changes"""
        if not self.github:
            raise Exception("GitHub API not available")
        
        self._ensure_local_repo()
        
        # Create a new branch
        repo = git.Repo(self.local_repo_path)
        branch_name = f"update-{file_path.replace('/', '-').replace('.', '-')}-{int(time.time() * 1000)}"
        
        # Create and checkout new branch
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        
        # Make changes
        full_path = os.path.join(self.local_repo_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Commit changes
        repo.index.add([file_path])
        repo.index.commit(f"Update {file_path}")
        
        # Push branch
        origin = repo.remotes.origin
        origin.push(refspec=f'{branch_name}:{branch_name}')
        
        # Create pull request
        github_repo = self.github.get_repo(self.repo_name)
        pr = github_repo.create_pull(
            title=title,
            body=description,
            head=branch_name,
            base='main'
        )
        
        # Switch back to main branch
        repo.heads.main.checkout()
        
        return pr.html_url
    
    def save_file_locally(self, file_path, content):
        """Save file to local repository without committing"""
        # Clean the file path to ensure it's relative
        clean_file_path = file_path
        if clean_file_path.startswith('/home/runner/workspace/local_repo/'):
            clean_file_path = clean_file_path.replace('/home/runner/workspace/local_repo/', '')
        elif clean_file_path.startswith('local_repo/'):
            clean_file_path = clean_file_path.replace('local_repo/', '')
        elif clean_file_path.startswith('/'):
            clean_file_path = clean_file_path.lstrip('/')
        
        full_path = os.path.join(self.local_repo_path, clean_file_path)
        
        # Create directory if it doesn't exist
        dir_path = os.path.dirname(full_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # Write content to file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logging.info(f"Saved file locally: {clean_file_path}")
    
    def delete_file(self, file_path):
        """Delete a file from local repository"""
        full_path = os.path.join(self.local_repo_path, file_path)
        
        if os.path.exists(full_path):
            os.remove(full_path)
            logging.info(f"Deleted file: {file_path}")
            return True
        return False
    
    def create_file(self, file_path, content=""):
        """Create a new file"""
        self.save_file_locally(file_path, content)
        return True
