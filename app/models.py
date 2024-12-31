from app import db
from werkzeug.security import generate_password_hash, check_password_hash

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # Badge name
    description = db.Column(db.Text, nullable=False)  # Badge description

    # Relationship to BadgeArtwork
    badge_artworks = db.relationship('BadgeArtwork', backref='badge', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Badge {self.name}>"


class ArtistSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Artist's full name
    email = db.Column(db.String(120), nullable=False)  # Email address
    phone_number = db.Column(db.String(15), nullable=True)  # Optional phone number
    artist_bio = db.Column(db.Text, nullable=False)  # Artist's biography
    portfolio_link = db.Column(db.String(255), nullable=True)  # Optional portfolio URL
    statement = db.Column(db.Text, nullable=False)  # Statement of interest
    demographic_identity = db.Column(db.Text, nullable=True)  # Optional demographic information
    lane_county_connection = db.Column(db.Text, nullable=True)  # Connection to Lane County
    accessibility_needs = db.Column(db.Text, nullable=True)  # Accessibility needs
    future_engagement = db.Column(db.Text, nullable=True)  # Future engagement interest
    consent_to_data = db.Column(db.Boolean, nullable=False, default=False)  # Consent to data usage
    opt_in_featured_artwork = db.Column(db.Boolean, nullable=False, default=False)

    # Relationship to BadgeArtwork
    badge_artworks = db.relationship('BadgeArtwork', backref='submission', cascade='all, delete-orphan')

    # Relationship to JudgeVote
    judge_votes = db.relationship('JudgeVote', backref='submission', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<ArtistSubmission name={self.name}, email={self.email}>"


class BadgeArtwork(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('artist_submission.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=False)
    artwork_file = db.Column(db.String(255), nullable=False)

    # Relationship to JudgeVote (for votes on a specific badge artwork)
    judge_votes = db.relationship('JudgeVote', backref='badge_artwork', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<BadgeArtwork Badge={self.badge.name}, File={self.artwork_file}>"


class Judge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    # Relationship to JudgeVote
    votes = db.relationship('JudgeVote', backref='judge', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Judge name={self.name}, is_admin={self.is_admin}>"


class JudgeVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judge_id = db.Column(db.Integer, db.ForeignKey('judge.id'), nullable=False)
    submission_id = db.Column(db.Integer, db.ForeignKey('artist_submission.id'), nullable=False)
    badge_artwork_id = db.Column(db.Integer, db.ForeignKey('badge_artwork.id'), nullable=False)
    rank = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<JudgeVote judge_id={self.judge_id}, badge_artwork_id={self.badge_artwork_id}, rank={self.rank}>"
