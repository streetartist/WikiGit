from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import Text

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    github_token = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    reviews = db.relationship('ContentReview', foreign_keys='ContentReview.author_id', backref='author', lazy=True)

class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ContentReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(500), nullable=False)
    original_content = db.Column(Text)
    modified_content = db.Column(Text)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    review_notes = db.Column(Text)
    version = db.Column(db.Integer, default=1)  # Version tracking for conflict handling
    merge_base = db.Column(Text)  # Base content for three-way merge
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    
    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref='reviewed_items', post_update=True)
