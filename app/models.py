from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from flask import url_for, current_app
from sqlalchemy.orm import relationship, backref

db = SQLAlchemy()

# Badge model to represent badges available for submissions
class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # Unique badge name
    description = db.Column(db.Text, nullable=False)  # Description of the badge
    badge_artworks = db.relationship('BadgeArtwork', backref='badge', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Badge {self.name}>"

# Artist submission model for adult artists
class ArtistSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Artist's full name
    email = db.Column(db.String(120), nullable=False)  # Email address (unique constraint can be added if necessary)
    phone_number = db.Column(db.String(15), nullable=True)  # Optional phone number
    artist_bio = db.Column(db.Text, nullable=False)  # Biography of the artist
    portfolio_link = db.Column(db.String(255), nullable=True)  # Optional link to portfolio
    statement = db.Column(db.Text, nullable=False)  # Artist's statement of interest
    demographic_identity = db.Column(db.Text, nullable=True)  # Optional demographic information
    lane_county_connection = db.Column(db.Text, nullable=True)  # Connection to Lane County
    hear_about_contest = db.Column(db.Text, nullable=True)  # Accessibility needs
    future_engagement = db.Column(db.Text, nullable=True)  # Interest in future engagement
    consent_to_data = db.Column(db.Boolean, nullable=False, default=False)  # Consent to data usage
    opt_in_featured_artwork = db.Column(db.Boolean, nullable=False, default=False)  # Opt-in for featuring artwork
    badge_artworks = db.relationship('BadgeArtwork', backref='submission', cascade='all, delete-orphan')
    judge_votes = db.relationship('JudgeVote', backref='artist_submission', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<ArtistSubmission name={self.name}, email={self.email}>"

# Youth artist submission model for submissions from young artists
class YouthArtistSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Youth artist's name
    age = db.Column(db.Integer, nullable=False)  # Age of the youth artist
    parent_contact_info = db.Column(db.Text, nullable=False)  # Parent's contact information
    email = db.Column(db.String(120), nullable=False)  # Youth artist's email
    about_why_design = db.Column(db.Text, nullable=False)  # Reason for designing the artwork
    about_yourself = db.Column(db.Text, nullable=False)  # Information about the youth artist
    badge_id = db.Column(db.Integer, db.ForeignKey("badge.id"), nullable=False)  # Reference to Badge
    artwork_file = db.Column(db.String(255), nullable=False)  # File path for the artwork
    opt_in_featured_artwork = db.Column(db.Boolean, nullable=False, default=False)  # Opt-in for featuring artwork
    parent_consent = db.Column(db.Boolean, nullable=False, default=False)  # Parent/Guardian consent
    
    badge = db.relationship("Badge", backref="youth_submissions")
    judge_votes = db.relationship('JudgeVote', backref='youth_submission', cascade='all, delete-orphan')


    def __repr__(self):
        return f"<YouthArtistSubmission name={self.name}, email={self.email}>"

# Badge artwork model representing artwork submissions tied to a badge
class BadgeArtwork(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('artist_submission.id', ondelete='CASCADE'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id', ondelete='CASCADE'), nullable=False)
    artwork_file = db.Column(db.String(255), nullable=False)  # File path for the artwork
    __table_args__ = (db.UniqueConstraint('submission_id', 'badge_id', name='unique_submission_badge'),)
    
    # One-to-many relationship with JudgeVote
    judge_votes = db.relationship('JudgeVote', backref='badge_artwork', cascade='all, delete-orphan')

    def __repr__(self):
        badge_name = self.badge.name if self.badge else "None"
        return f"<BadgeArtwork Badge={badge_name}, File={self.artwork_file}>"

# User model for user authentication and voting
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    # Relationship to JudgeVote
    votes = db.relationship('JudgeVote', backref='user', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set the password for the judge."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hashed password."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User name={self.name}, is_admin={self.is_admin}>"


# User vote model representing votes cast by judges
class JudgeVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Make sure it references 'user.id'
    submission_id = db.Column(db.Integer, db.ForeignKey('artist_submission.id'), nullable=True)
    youth_submission_id = db.Column(db.Integer, db.ForeignKey('youth_artist_submission.id'), nullable=True)
    badge_artwork_id = db.Column(db.Integer, db.ForeignKey('badge_artwork.id'), nullable=False)
    rank = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        if self.submission_id:
            return f"<JudgeVote submission_id={self.submission_id}>"
        return f"<JudgeVote youth_submission_id={self.youth_submission_id}>"


# Submission period model to control submission timings
class SubmissionPeriod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_start = db.Column(db.DateTime(timezone=True), nullable=False)  # Start time of the submission period
    submission_end = db.Column(db.DateTime(timezone=True), nullable=False)  # End time of the submission period

    def __repr__(self):
        return f"<SubmissionPeriod start={self.submission_start}, end={self.submission_end}>"
