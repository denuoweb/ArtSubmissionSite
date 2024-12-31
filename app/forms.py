
from flask_wtf import FlaskForm
from wtforms import Form, FormField, IntegerField, HiddenField, FieldList, BooleanField, PasswordField, StringField, TextAreaField, FileField, SubmitField, SelectField
from wtforms.validators import Regexp, NumberRange, DataRequired, Email, URL, Optional, Length, ValidationError
from flask_wtf.file import FileAllowed
from urllib.parse import urlparse
import re

def file_size_limit(max_size_mb):
    def _file_size_limit(form, field):
        # Check if the field contains a file (FileStorage object)
        if field.data and hasattr(field.data, "read"):  # Only validate if it's a file object
            file_size = len(field.data.read())  # Get the file size in bytes
            field.data.seek(0)  # Reset file pointer after reading
            max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
            if file_size > max_size_bytes:
                raise ValidationError(f"File size must not exceed {max_size_mb} MB.")
        elif isinstance(field.data, str):
            # If `field.data` is a string (previously uploaded file), skip validation
            return
    return _file_size_limit
    

class BadgeUploadForm(Form):
    badge_id = SelectField(
        "Select a Badge",
        coerce=int,
        validators=[DataRequired(message="Please select a badge.")],
    )
    artwork_file = FileField(
        "Upload Artwork",
        validators=[
            DataRequired(message="Please upload your artwork file."),
            FileAllowed(
                ["jpg", "jpeg", "png", "svg"],
                message="Only JPG, JPEG, PNG, or SVG files are allowed."
            ),
            file_size_limit(8)  # Limit file size to 8 MB
        ],
    )

class ArtistSubmissionForm(FlaskForm):
    # Personal Information
    name = StringField(
        "Name", 
        validators=[
            DataRequired(message="Your name is required."),
            Length(max=100, message="Name cannot exceed 100 characters.")
        ],
        render_kw={"placeholder": "Enter your full name"}
    )
    email = StringField(
        "Email", 
        validators=[
            DataRequired(message="Your email is required."),
            Email(message="Please provide a valid email address.")
        ],
        render_kw={"placeholder": "Enter your email address"}
    )
    phone_number = StringField(
        "Phone Number", 
        validators=[
            Optional(),
            Length(max=15, message="Phone number cannot exceed 15 digits."),
            Regexp(r'^[0-9\s\-()]+$', message="Phone number must contain only digits, spaces, hyphens, or parentheses.")
        ],
        render_kw={"placeholder": "Enter your phone number"}
    )
    artist_bio = TextAreaField(
        "Artist Bio (1,000 to 2,500 characters)", 
        validators=[
            DataRequired(message="Please provide a brief artist bio."),
            Length(min=1000, max=2500, message="Bio must be between 1,000 to 2,500 characters.")
        ],
        render_kw={"placeholder": "Write a brief bio about yourself."}
    )
    portfolio_link = StringField(
        "Portfolio Link", 
        validators=[
            Optional(),
            Length(max=255, message="Portfolio URL cannot exceed 255 characters.")
        ],
        render_kw={"placeholder": "Provide a link to your online portfolio (if available)"}
    )
    statement = TextAreaField(
        "Statement of Interest (1,000 to 2,500 characters)", 
        validators=[
            DataRequired(message="Please provide your statement of interest."),
            Length(min=1000, max=2500, message="Statement must be between 1,000 to 2,500 characters.")
        ],
        render_kw={"placeholder": "Why do you want to contribute? How does your work reflect bicycling?"}
    )
    
    # Badge Uploads
    badge_uploads = FieldList(
        FormField(BadgeUploadForm),
        min_entries=1,
        max_entries=3,
        validators=[
            DataRequired(message="Please provide at least one badge and artwork.")
        ]
    )
    
    # Demographic Information
    demographic_identity = StringField(
        "How would you describe your identity?",
        validators=[
            Optional(),
            Length(max=200, message="Identity description cannot exceed 200 characters.")
        ],
        render_kw={"placeholder": "Race, ethnicity, gender identity, or age"}
    )
    lane_county_connection = TextAreaField(
        "Are you a resident of Lane County or connected to the local community? (500 characters max)",
        validators=[
            Optional(),
            Length(max=500, message="Response cannot exceed 500 characters.")
        ],
        render_kw={"placeholder": "Describe your connection to Lane County."}
    )
    accessibility_needs = TextAreaField(
        "Do you have any accessibility needs we can accommodate?  (500 characters max)",
        validators=[
            Optional(),
            Length(max=500, message="Response cannot exceed 500 characters. (500 characters max)")
        ],
        render_kw={"placeholder": "Translation services, assistance, etc."}
    )
    future_engagement = TextAreaField(
        "Are you interested in being involved in future projects? (500 characters max)",
        validators=[
            Optional(),
            Length(max=500, message="Response cannot exceed 500 characters.")
        ],
        render_kw={"placeholder": "Describe your interest in future involvement."}
    )
    
    # Consent and Opt-In
    consent_to_data = BooleanField(
        "Do you consent to the Terms and Conditions?",
        validators=[DataRequired(message="Please provide your consent.")],
        default=False
    )
    opt_in_featured_artwork = BooleanField(
        "Feature All Submitted Artwork (Voluntary Opt-In)",
        default=False
    )
    
    # Submit Button
    submit = SubmitField("Submit")

class YouthArtistSubmissionForm(FlaskForm):
    # Personal Information
    name = StringField(
        "Name (First and Last)",
        validators=[
            DataRequired(message="Your name is required."),
            Length(max=100, message="Name cannot exceed 100 characters.")
        ],
        render_kw={"placeholder": "Enter your full name"}
    )
    age = IntegerField(
        "Age",
        validators=[
            DataRequired(message="Your age is required."),
            NumberRange(min=13, max=17, message="Age must be between 13 and 18.")
        ],
        render_kw={"placeholder": "Enter your age"}
    )
    parent_contact_info = TextAreaField(
        "Parent/Guardian Name and Contact Information",
        validators=[
            DataRequired(message="Parent/Guardian contact information is required."),
            Length(max=300, message="Contact information cannot exceed 300 characters.")
        ],
        render_kw={"placeholder": "Enter name, phone number, and/or email of parent/guardian"}
    )
    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Your email address is required."),
            Email(message="Please provide a valid email address.")
        ],
        render_kw={"placeholder": "Enter your contact email"}
    )

    # About You
    about_why_design = TextAreaField(
        "Why do you want to design a badge for Quest by Cycle?",
        validators=[
            DataRequired(message="This field is required."),
            Length(max=500, message="Response cannot exceed 500 characters.")
        ],
        render_kw={"placeholder": "Tell us what excites you about this project."}
    )
    about_yourself = TextAreaField(
        "Tell us a little about yourself and your interest in art!",
        validators=[
            DataRequired(message="This field is required."),
            Length(max=500, message="Response cannot exceed 500 characters.")
        ],
        render_kw={"placeholder": "For example: How long have you been creating art? What inspires you?"}
    )

    # Badge Design Information
    badge_id = SelectField(
        "Badge Name",
        coerce=lambda x: int(x) if x and str(x).isdigit() else None,  # Safely handle None or invalid values
        validators=[DataRequired(message="Please select a badge.")],  # Ensure a valid badge is selected
    )
    artwork_file = FileField(
        "Upload Artwork",
        validators=[
            DataRequired(message="Please upload your artwork file."),
            FileAllowed(["jpg", "jpeg", "png", "svg"], message="Only JPG, PNG, or SVG files are allowed."),
            file_size_limit(8)  # Limit file size to 8 MB
        ],
    )

    # Parent Consent
    parent_consent = BooleanField(
        "Parent/Guardian Consent",
        validators=[DataRequired(message="Parent/Guardian consent is required.")],
        default=False
    )

    submit = SubmitField("Submit")


class PasswordForm(FlaskForm):
    password = PasswordField(
        "", 
        validators=[DataRequired(), Length(min=4, max=20)],
        render_kw={"placeholder": "Password"}
    )
    submit = SubmitField("Submit")


class RankingForm(FlaskForm):
    rank = HiddenField("Rank")
    submit = SubmitField("Submit Rankings")  # Add a SubmitField