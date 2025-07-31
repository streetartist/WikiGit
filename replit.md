# Wiki Documentation System

## Overview

This is a Flask-based wiki documentation system with GitHub integration, designed for collaborative editing and reviewing of documentation files. The system provides role-based access control, a review workflow for content changes, and seamless synchronization with GitHub repositories.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with SQLite (default) or PostgreSQL support
- **Authentication**: Flask-Login for session management
- **Security**: Werkzeug for password hashing and security utilities

### Frontend Architecture
- **Templates**: Jinja2 templating engine
- **Styling**: Bootstrap 5 with dark theme
- **JavaScript**: Vanilla JS with CodeMirror for code editing
- **Icons**: Font Awesome for UI icons

### Database Schema
The system uses three main models:
- **User**: Stores user accounts with role-based permissions (admin/regular user)
- **SystemConfig**: Key-value store for system-wide configuration
- **ContentReview**: Tracks content changes and review workflow

## Key Components

### Authentication System
- User registration and login functionality
- Role-based access control (admin vs regular users)
- Default admin account with credentials (admin/wenjiaxian88)
- Personal GitHub token storage for individual users

### File Management
- GitHub repository integration for file storage
- Local repository synchronization
- File browser with tree structure navigation
- Code editor with syntax highlighting using CodeMirror
- Support for various file types with appropriate syntax highlighting

### Review Workflow
- Content changes require review approval (except for admin direct sync)
- Diff visualization for reviewing changes
- Approval/rejection system with review notes
- Queue management for pending reviews

### GitHub Integration
- Repository cloning and synchronization
- Personal access token management
- File tree browsing from GitHub repository
- Automatic pulling of latest changes

## Data Flow

1. **File Editing Flow**:
   - User browses files → selects file → edits in CodeMirror → saves changes
   - Regular users: changes go to review queue
   - Admin users: option for direct sync to GitHub

2. **Review Flow**:
   - Content changes create ContentReview records
   - Admins review changes in queue
   - Approval triggers sync to GitHub repository
   - Rejection notifies author with feedback

3. **Synchronization Flow**:
   - System maintains local copy of GitHub repository
   - Periodic sync pulls latest changes
   - Approved changes push back to GitHub

## External Dependencies

### Python Packages
- Flask and Flask extensions (SQLAlchemy, Login)
- PyGithub for GitHub API integration
- GitPython for Git operations
- Werkzeug for security utilities

### Frontend Libraries
- Bootstrap 5 (via CDN)
- CodeMirror for code editing
- Font Awesome for icons
- Custom CSS for styling

### GitHub Integration
- Requires GitHub Personal Access Token with 'repo' permissions
- Repository must be accessible to the configured token
- Uses GitHub API for repository operations

## Deployment Strategy

### Configuration
- Environment variables for database URL and session secrets
- System configuration stored in database (GitHub tokens, repository info)
- Support for both development (SQLite) and production (PostgreSQL) databases

### Security Considerations
- Password hashing using Werkzeug
- Session management with Flask-Login
- GitHub tokens stored securely in database
- WSGI proxy fix for deployment behind reverse proxies

### Development Setup
- Default SQLite database for local development
- Debug mode enabled in main.py
- Automatic database table creation on startup
- Default admin user creation if not exists

The system is designed to be deployed on platforms like Replit, with support for environment-based configuration and automatic initialization of required database tables and default users.