import os
import logging
from flask import render_template, request, redirect, url_for, flash, jsonify, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from app import app, db
from models import User, SystemConfig, ContentReview
from github_service import GitHubService
from utils import get_file_extension, is_text_file, format_diff

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('register.html')
        
        # Create new user
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/files')
@login_required
def file_browser():
    github_service = GitHubService()
    try:
        files = github_service.get_file_tree()
        return render_template('file_browser.html', files=files)
    except Exception as e:
        flash(f'Error loading files: {str(e)}', 'danger')
        return render_template('file_browser.html', files=[])

@app.route('/edit/<path:file_path>')
@login_required
def edit_file(file_path):
    github_service = GitHubService()
    try:
        content = github_service.get_file_content(file_path)
        file_extension = get_file_extension(file_path)
        return render_template('editor.html', 
                             file_path=file_path, 
                             content=content, 
                             file_extension=file_extension)
    except Exception as e:
        flash(f'Error loading file: {str(e)}', 'danger')
        return redirect(url_for('file_browser'))

@app.route('/save_file', methods=['POST'])
@login_required
def save_file():
    file_path = request.form['file_path']
    content = request.form['content']
    action = request.form['action']  # 'review', 'direct_sync', 'create_pr', 'direct_pr'
    
    github_service = GitHubService()
    
    try:
        if action == 'review':
            # Submit for review (users only) - save locally first
            github_service.save_file_locally(file_path, content)
            original_content = github_service.get_file_content(file_path) if github_service.file_exists(file_path) else ""
            
            # Clean the file path more thoroughly
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
            
            # Remove leading slashes
            clean_file_path = clean_file_path.lstrip('/')
            
            logging.info(f"Saving review - Original path: {file_path}, Cleaned path: {clean_file_path}")
            
            review = ContentReview(
                file_path=clean_file_path,
                original_content=original_content,
                modified_content=content,
                author_id=current_user.id
            )
            db.session.add(review)
            db.session.commit()
            flash('Changes saved and submitted for review', 'success')
            
        elif action == 'direct_sync' and current_user.is_admin:
            # Direct sync to main branch (admin only)
            commit_message = request.form.get('commit_message', f'Update {file_path}')
            if github_service.token and github_service.repo_name:
                github_service.commit_and_push(file_path, content, commit_message)
                flash('Changes synced to GitHub', 'success')
            else:
                github_service.save_file_locally(file_path, content)
                flash('File saved locally (GitHub not configured)', 'warning')
            
        elif action == 'create_pr' and current_user.is_admin:
            # Create PR from admin account
            pr_title = request.form.get('pr_title', f'Update {file_path}')
            pr_description = request.form.get('pr_description', '')
            if github_service.token and github_service.repo_name:
                pr_url = github_service.create_pull_request(file_path, content, pr_title, pr_description)
                flash(f'Pull request created: <a href="{pr_url}" target="_blank">View PR</a>', 'success')
            else:
                github_service.save_file_locally(file_path, content)
                flash('File saved locally (GitHub not configured for PR)', 'warning')
            
        elif action == 'direct_pr':
            # Create PR using user's token
            if not current_user.github_token:
                flash('Please configure your GitHub token in settings', 'danger')
                return redirect(url_for('edit_file', file_path=file_path))
            
            pr_title = request.form.get('pr_title', f'Update {file_path}')
            pr_description = request.form.get('pr_description', '')
            user_github_service = GitHubService(token=current_user.github_token)
            pr_url = user_github_service.create_pull_request(file_path, content, pr_title, pr_description)
            flash(f'Pull request created: <a href="{pr_url}" target="_blank">View PR</a>', 'success')
        else:
            # Default save action
            github_service.save_file_locally(file_path, content)
            flash('File saved successfully', 'success')
        
        return redirect(url_for('file_browser'))
        
    except Exception as e:
        error_details = str(e)
        logging.error(f"Error saving file {file_path}: {error_details}")
        
        # Provide more specific error messages
        if "Git operation failed" in error_details:
            flash(f'Git操作失败: {error_details}', 'danger')
        elif "GitHub token" in error_details.lower():
            flash(f'GitHub配置错误: 请检查GitHub令牌设置', 'danger')
        elif "repository" in error_details.lower():
            flash(f'仓库配置错误: 请检查仓库设置', 'danger')
        else:
            flash(f'文件保存失败: {error_details}', 'danger')
        
        return redirect(url_for('edit_file', file_path=file_path))

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)
    
    pending_reviews = ContentReview.query.filter_by(status='pending').count()
    total_users = User.query.count()
    
    return render_template('admin_dashboard.html', 
                         pending_reviews=pending_reviews, 
                         total_users=total_users)

@app.route('/reviews')
@login_required
def review_queue():
    if not current_user.is_admin:
        abort(403)
    
    reviews = ContentReview.query.filter_by(status='pending').order_by(ContentReview.created_at.desc()).all()
    return render_template('review_queue.html', reviews=reviews)

@app.route('/review/<int:review_id>')
@login_required
def view_review(review_id):
    if not current_user.is_admin:
        abort(403)
    
    review = ContentReview.query.get_or_404(review_id)
    diff_html = format_diff(review.original_content or "", review.modified_content or "")
    
    return render_template('diff_view.html', review=review, diff_html=diff_html)

@app.route('/approve_review/<int:review_id>', methods=['POST'])
@login_required
def approve_review(review_id):
    if not current_user.is_admin:
        abort(403)
    
    review = ContentReview.query.get_or_404(review_id)
    review_notes = request.form.get('review_notes', '')
    
    try:
        # Apply the changes to the repository
        github_service = GitHubService()
        
        # Clean the file path to remove any absolute path prefixes - more comprehensive cleaning
        file_path = review.file_path
        
        # Remove various possible path prefixes
        path_prefixes = [
            '/home/runner/workspace/local_repo/',
            '/home/runner/workspace/local_repo',
            'local_repo/',
            'local_repo',
            '/workspace/local_repo/',
            '/workspace/local_repo'
        ]
        
        for prefix in path_prefixes:
            if file_path.startswith(prefix):
                file_path = file_path[len(prefix):]
                break
        
        # Remove leading slashes
        file_path = file_path.lstrip('/')
        
        # Ensure we have a valid relative path
        if not file_path:
            raise Exception("Invalid file path after cleaning")
        
        logging.info(f"Original path: {review.file_path}, Cleaned path: {file_path}")
        
        commit_message = f'Approved changes to {file_path} by {review.author.username}'
        github_service.commit_and_push(file_path, review.modified_content, commit_message)
        
        # Update review status
        review.status = 'approved'
        review.reviewer_id = current_user.id
        review.review_notes = review_notes
        review.reviewed_at = datetime.utcnow()
        db.session.commit()
        
        flash('Review approved and changes merged', 'success')
    except Exception as e:
        error_details = str(e)
        logging.error(f"Error approving review {review_id}: {error_details}")
        
        # Provide more specific error messages
        if "Git operation failed" in error_details:
            flash(f'Git操作失败: {error_details}', 'danger')
        elif "GitHub token" in error_details.lower():
            flash(f'GitHub配置错误: {error_details}. 请检查GitHub设置。', 'danger')
        elif "repository" in error_details.lower():
            flash(f'仓库错误: {error_details}. 请检查仓库配置。', 'danger')
        else:
            flash(f'审核失败: {error_details}', 'danger')
    
    return redirect(url_for('review_queue'))

@app.route('/reject_review/<int:review_id>', methods=['POST'])
@login_required
def reject_review(review_id):
    if not current_user.is_admin:
        abort(403)
    
    review = ContentReview.query.get_or_404(review_id)
    review_notes = request.form.get('review_notes', '')
    
    review.status = 'rejected'
    review.reviewer_id = current_user.id
    review.review_notes = review_notes
    review.reviewed_at = datetime.utcnow()
    db.session.commit()
    
    flash('Review rejected', 'info')
    return redirect(url_for('review_queue'))

@app.route('/sync_repository', methods=['POST'])
@login_required
def sync_repository():
    if not current_user.is_admin:
        abort(403)
    
    try:
        github_service = GitHubService()
        github_service.sync_repository()
        flash('Repository synchronized successfully', 'success')
    except Exception as e:
        flash(f'Error syncing repository: {str(e)}', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if not current_user.is_admin:
        abort(403)
    
    if request.method == 'POST':
        github_token = request.form['github_token']
        github_repo = request.form['github_repo']
        
        # Save or update configuration
        token_config = SystemConfig.query.filter_by(key='github_token').first()
        if token_config:
            token_config.value = github_token
            token_config.updated_at = datetime.utcnow()
        else:
            token_config = SystemConfig(key='github_token', value=github_token)
            db.session.add(token_config)
        
        repo_config = SystemConfig.query.filter_by(key='github_repo').first()
        if repo_config:
            repo_config.value = github_repo
            repo_config.updated_at = datetime.utcnow()
        else:
            repo_config = SystemConfig(key='github_repo', value=github_repo)
            db.session.add(repo_config)
        
        db.session.commit()
        flash('Settings saved successfully', 'success')
        return redirect(url_for('settings'))
    
    # Get current settings
    github_token = SystemConfig.query.filter_by(key='github_token').first()
    github_repo = SystemConfig.query.filter_by(key='github_repo').first()
    users = User.query.all()
    
    return render_template('settings.html', 
                         github_token=github_token.value if github_token else '',
                         github_repo=github_repo.value if github_repo else '',
                         users=users)

@app.route('/user_settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    if request.method == 'POST':
        github_token = request.form['github_token']
        current_user.github_token = github_token
        db.session.commit()
        flash('GitHub token saved successfully', 'success')
        return redirect(url_for('user_settings'))
    
    return render_template('user_settings.html')

@app.route('/create_file', methods=['GET', 'POST'])
@login_required
def create_file():
    if request.method == 'POST':
        file_path = request.form['file_path']
        content = request.form.get('content', '')
        action = request.form.get('action', 'review')  # Default to review for new files
        
        github_service = GitHubService()
        
        try:
            if github_service.file_exists(file_path):
                flash('File already exists', 'danger')
                return render_template('create_file.html')
            
            if action == 'review':
                # Submit for review (users only) - save locally first
                github_service.save_file_locally(file_path, content)
                
                # Clean the file path
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
                
                clean_file_path = clean_file_path.lstrip('/')
                
                logging.info(f"Creating file for review - Original path: {file_path}, Cleaned path: {clean_file_path}")
                
                review = ContentReview(
                    file_path=clean_file_path,
                    original_content="",  # New file, so original content is empty
                    modified_content=content,
                    author_id=current_user.id
                )
                db.session.add(review)
                db.session.commit()
                flash('New file created and submitted for review', 'success')
                
            elif action == 'direct_sync' and current_user.is_admin:
                # Direct sync to main branch (admin only)
                commit_message = request.form.get('commit_message', f'Create {file_path}')
                if github_service.token and github_service.repo_name:
                    github_service.commit_and_push(file_path, content, commit_message)
                    flash('File created and synced to GitHub', 'success')
                else:
                    github_service.save_file_locally(file_path, content)
                    flash('File created locally (GitHub not configured)', 'warning')
                
            elif action == 'create_pr' and current_user.is_admin:
                # Create PR from admin account
                pr_title = request.form.get('pr_title', f'Create {file_path}')
                pr_description = request.form.get('pr_description', '')
                if github_service.token and github_service.repo_name:
                    pr_url = github_service.create_pull_request(file_path, content, pr_title, pr_description)
                    flash(f'File created and pull request created: <a href="{pr_url}" target="_blank">View PR</a>', 'success')
                else:
                    github_service.save_file_locally(file_path, content)
                    flash('File created locally (GitHub not configured for PR)', 'warning')
                
            elif action == 'direct_pr':
                # Create PR using user's token
                if not current_user.github_token:
                    flash('Please configure your GitHub token in settings', 'danger')
                    return render_template('create_file.html')
                
                pr_title = request.form.get('pr_title', f'Create {file_path}')
                pr_description = request.form.get('pr_description', '')
                user_github_service = GitHubService(token=current_user.github_token)
                pr_url = user_github_service.create_pull_request(file_path, content, pr_title, pr_description)
                flash(f'File created and pull request created: <a href="{pr_url}" target="_blank">View PR</a>', 'success')
            else:
                # Default save action
                github_service.save_file_locally(file_path, content)
                flash('File created successfully', 'success')
            
            return redirect(url_for('file_browser'))
            
        except Exception as e:
            error_details = str(e)
            logging.error(f"Error creating file {file_path}: {error_details}")
            
            # Provide more specific error messages
            if "Git operation failed" in error_details:
                flash(f'Git操作失败: {error_details}', 'danger')
            elif "GitHub token" in error_details.lower():
                flash(f'GitHub配置错误: 请检查GitHub令牌设置', 'danger')
            elif "repository" in error_details.lower():
                flash(f'仓库配置错误: 请检查仓库设置', 'danger')
            else:
                flash(f'文件创建失败: {error_details}', 'danger')
            
            return render_template('create_file.html')
    
    return render_template('create_file.html')

@app.route('/delete_file/<path:file_path>', methods=['POST'])
@login_required
def delete_file(file_path):
    if not current_user.is_admin:
        flash('Only administrators can delete files', 'danger')
        return redirect(url_for('file_browser'))
    
    github_service = GitHubService()
    
    try:
        if github_service.delete_file(file_path):
            flash('File deleted successfully', 'success')
        else:
            flash('File not found', 'warning')
            
    except Exception as e:
        flash(f'Error deleting file: {str(e)}', 'danger')
    
    return redirect(url_for('file_browser'))

@app.route('/promote_user/<int:user_id>', methods=['POST'])
@login_required
def promote_user(user_id):
    if not current_user.is_admin:
        abort(403)
    
    user = User.query.get_or_404(user_id)
    user.is_admin = True
    db.session.commit()
    
    flash(f'User {user.username} promoted to admin', 'success')
    return redirect(url_for('settings'))

@app.route('/demote_user/<int:user_id>', methods=['POST'])
@login_required
def demote_user(user_id):
    if not current_user.is_admin:
        abort(403)
    
    user = User.query.get_or_404(user_id)
    if user.username == 'admin':
        flash('Cannot demote the default admin user', 'danger')
        return redirect(url_for('settings'))
    
    user.is_admin = False
    db.session.commit()
    
    flash(f'User {user.username} demoted to regular user', 'info')
    return redirect(url_for('settings'))
