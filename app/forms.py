from flask_wtf import FlaskForm
from wtforms import HiddenField, BooleanField, PasswordField, StringField, TextAreaField, FileField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, URL, Optional, Length
from flask_wtf.file import FileAllowed

class ArtistSubmissionForm(FlaskForm):
    name = StringField(
        "Name", 
        validators=[DataRequired(message="Your name is required.")],
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
        "Phone Number (optional)", 
        validators=[Optional()],
        render_kw={"placeholder": "Enter your phone number"}
    )
    artist_bio = TextAreaField(
        "Artist Bio", 
        validators=[
            DataRequired(message="Please provide a brief artist bio."),
            Length(min=100, max=200, message="Bio must be between 100-200 words.")
        ],
        render_kw={"placeholder": "Write a brief bio about yourself (100-200 words)"}
    )
    portfolio_link = StringField(
        "Portfolio Link (optional)", 
        validators=[Optional(), URL(message="Please provide a valid URL.")],
        render_kw={"placeholder": "Provide a link to your online portfolio (if available)"}
    )
    statement = TextAreaField(
        "Statement of Interest", 
        validators=[
            DataRequired(message="Please provide your statement of interest."),
            Length(max=250, message="Statement must not exceed 250 words.")
        ],
        render_kw={"placeholder": "Why do you want to contribute? How does your work reflect diversity?"}
    )
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
                ["jpg", "jpeg", "png", "pdf"], 
                message="Only JPG, JPEG, PNG, and PDF files are allowed."
            )
        ],
        render_kw={"multiple": True}  # Support multiple files
    )
    cultural_engagement = TextAreaField(
        "How does your design reflect the cultural diversity, history, or values of Lane County?",
        validators=[DataRequired(message="This field is required.")],
        render_kw={"placeholder": "Explain the cultural relevance of your design."}
    )
    community_impact = TextAreaField(
        "What impact do you hope your design will have on the community?",
        validators=[DataRequired(message="This field is required.")],
        render_kw={"placeholder": "Describe the intended impact of your design."}
    )
    sustainability_importance = TextAreaField(
        "Why is sustainability important to you, and how is it reflected in your badge design?",
        validators=[DataRequired(message="This field is required.")],
        render_kw={"placeholder": "Explain how sustainability influences your design."}
    )
    demographic_identity = StringField(
        "How do you identify? (optional)",
        render_kw={"placeholder": "Race, ethnicity, gender identity, or age (optional)"}
    )
    lane_county_connection = TextAreaField(
        "Are you a resident of Lane County or connected to the local community?",
        validators=[Optional()],
        render_kw={"placeholder": "Describe your connection to Lane County."}
    )
    accessibility_needs = TextAreaField(
        "Do you have any accessibility needs we can accommodate?",
        validators=[Optional()],
        render_kw={"placeholder": "Translation services, assistance, etc."}
    )
    future_engagement = TextAreaField(
        "If yes, tell us how you'd like to be involved in future projects.",
        validators=[Optional()],
        render_kw={"placeholder": "Describe your interest in future involvement."}
    )
    consent_to_data = BooleanField(
        "Do you consent to the Terms and Conditions?",
        validators=[DataRequired(message="Please provide your consent.")],
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