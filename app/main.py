from flask import Blueprint, jsonify, render_template, request, redirect, flash, session, abort, make_response, current_app
from flask_wtf.csrf import generate_csrf, validate_csrf, CSRFError
from flask_login import login_required, current_user
from app.auth import judges
from app.admin import is_submission_open
from app.models import ArtistSubmission, YouthArtistSubmission, User, JudgeVote, Badge, BadgeArtwork, SubmissionPeriod, db
from app.forms import ArtistSubmissionForm, RankingForm, YouthArtistSubmissionForm, LogoutForm
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from app.utils import custom_url_for as url_for
from functools import wraps

import os
import uuid
import logging
import traceback

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


def csrf_exempt_route(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except CSRFError as e:
            return jsonify({'success': False, 'message': 'CSRF token missing or invalid.'}), 400
        return f(*args, **kwargs)
    return decorated_function


@main_bp.route("/delete_cached_image", methods=["POST"])
@csrf_exempt_route
def delete_cached_image():
    data = request.get_json()
    if not data or 'file_path' not in data:
        logger.warning("Delete cached image request missing 'file_path'.")
        return jsonify({'success': False, 'message': 'Invalid request data.'}), 400

    file_path = data['file_path']
    logger.debug(f"Attempting to delete file: {file_path}")

    # Security check: Ensure the file is within the upload directory
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    if not upload_folder:
        logger.error("UPLOAD_FOLDER not configured.")
        return jsonify({'success': False, 'message': 'Server configuration error.'}), 500

    # Resolve the absolute path
    absolute_file_path = os.path.abspath(file_path)

    # Ensure the file is within the upload directory
    if not absolute_file_path.startswith(os.path.abspath(upload_folder)):
        logger.warning(f"Attempted to delete a file outside the upload directory: {absolute_file_path}")
        return jsonify({'success': False, 'message': 'Unauthorized file path.'}), 403

    # Check if the file exists
    if not os.path.exists(absolute_file_path):
        logger.warning(f"File not found: {absolute_file_path}")
        return jsonify({'success': False, 'message': 'File does not exist.'}), 404

    try:
        os.remove(absolute_file_path)
        logger.info(f"Deleted cached image: {absolute_file_path}")
        return jsonify({'success': True, 'message': 'File deleted successfully.'}), 200
    except Exception as e:
        logger.error(f"Error deleting file {absolute_file_path}: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': 'Failed to delete the file.'}), 500

@main_bp.route("/")
def index():
    submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()
    submission_open = is_submission_open()
    submission_status = "Open" if submission_open else "Closed"
    if submission_period:
        pacific = ZoneInfo("US/Pacific")
        submission_start = submission_period.submission_start.astimezone(pacific).strftime("%B %d, %Y at %I:%M %p %Z")
        submission_deadline = submission_period.submission_end.astimezone(pacific).strftime("%B %d, %Y at %I:%M %p %Z")
    else:
        submission_start = "N/A"
        submission_deadline = "N/A"

    badges = Badge.query.all()

    return render_template(
        "index.html",
        submission_status=submission_status,
        submission_start=submission_start,
        submission_deadline=submission_deadline,
        badges=badges
    )


def get_rank_suffix(rank):
    """Return the appropriate suffix for a given rank."""
    if rank % 100 in (11, 12, 13):  # Special case for 11th, 12th, 13th
        return "th"
    if rank % 10 == 1:
        return "st"
    if rank % 10 == 2:
        return "nd"
    if rank % 10 == 3:
        return "rd"
    return "th"


def save_rankings_for_user(user_id, ranked_ids):
    rank = 1
    with db.session.begin_nested():
        db.session.query(JudgeVote).filter_by(user_id=user_id).delete()
        for submission_id in ranked_ids:
            badge_artwork = db.session.query(BadgeArtwork).filter_by(submission_id=submission_id).first()
            if not badge_artwork:
                raise ValueError(f"No BadgeArtwork found for submission ID: {submission_id}")
            vote = JudgeVote(
                user_id=user_id,
                submission_id=submission_id,
                rank=rank,
                badge_artwork_id=badge_artwork.id
            )
            db.session.add(vote)
            rank += 1
    db.session.commit()


@main_bp.route("/judges/ballot", methods=["GET", "POST"])
@login_required
def judges_ballot():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not current_user.is_authenticated:
        logger.warning("Unauthorized access attempt.")
        flash("Unauthorized access. Privileges required.", "danger")
        return redirect(url_for("main.index"))

    logger.info(f"User {current_user.id} ({current_user.name}) accessed judges ballot.")

    logout_form = LogoutForm()
    rank_form = RankingForm()
    user_id = current_user.id

    prepared_artist_submissions = []
    prepared_youth_submissions = []

    if request.method == "POST":
        logger.debug("Received POST request.")
        if rank_form.validate_on_submit():
            logger.debug("Form validation successful.")
            form_name = request.form.get("form_name")
            rank_data = request.form.get("rank")

            logger.debug(f"Form name received: {form_name}")
            logger.debug(f"Ranked votes received: {rank_data}")

            if not rank_data:
                logger.warning("No ranked votes received in the request.")
                flash("No ranked votes were provided.", "danger")
                return jsonify({"error": "No rankings submitted"}), 400

            try:
                # Parse rankings and handle them
                ranked_ids = rank_data.split(",")
                logger.debug(f"Parsed ranked IDs: {ranked_ids}")

                # Save rankings to the database for the current user
                save_rankings_for_user(user_id, ranked_ids)

                flash("Rankings submitted successfully!", "success")
                return jsonify({"success": True}), 200
            except Exception as e:
                logger.error("An error occurred during the transaction.", exc_info=True)
                flash("An error occurred while saving rankings. Please try again.", "danger")
                return jsonify({"error": "An error occurred"}), 500
        else:
            logger.warning("Form validation failed.")
            flash("Form validation failed. Please try again.", "danger")

    # Retrieve saved votes
    logger.debug(f"Retrieving saved votes for user_id: {user_id}")
    saved_votes = db.session.query(JudgeVote).filter_by(user_id=user_id).order_by(JudgeVote.rank).all()
    logger.debug(f"Saved votes retrieved: {saved_votes}")
    ranked_submission_ids = [vote.submission_id for vote in saved_votes]

    # Retrieve artist submissions
    logger.debug("Retrieving artist submissions.")
    artist_submissions = db.session.query(
        ArtistSubmission.id,
        ArtistSubmission.name,
        ArtistSubmission.email,
        ArtistSubmission.artist_bio,
        ArtistSubmission.portfolio_link,
        ArtistSubmission.statement,
        BadgeArtwork.artwork_file.label("artwork_file"),
        Badge.id.label("badge_id"),
        Badge.name.label("badge_name"),
    ).join(
        BadgeArtwork, BadgeArtwork.submission_id == ArtistSubmission.id
    ).join(
        Badge, BadgeArtwork.badge_id == Badge.id
    ).distinct().all()
    logger.debug(f"Artist submissions retrieved: {len(artist_submissions)}")

    # Prepare artist submissions
    if saved_votes:
        logger.debug("Sorting submissions based on saved votes.")
        ranked_submissions = [
            submission for submission in artist_submissions if submission.id in ranked_submission_ids
        ]
        ranked_submissions.sort(key=lambda s: ranked_submission_ids.index(s.id))
        unranked_submissions = [
            submission for submission in artist_submissions if submission.id not in ranked_submission_ids
        ]
        prepared_artist_submissions = ranked_submissions + unranked_submissions
    else:
        logger.debug("No saved votes. Preparing random order for submissions.")
        if "random_artist_order" not in session:
            random_order = [submission.id for submission in artist_submissions]
            import random
            random.shuffle(random_order)
            session["random_artist_order"] = random_order
        else:
            random_order = session["random_artist_order"]

        prepared_artist_submissions = sorted(
            artist_submissions, key=lambda s: random_order.index(s.id)
        )

    # Retrieve youth submissions
    logger.debug("Retrieving youth submissions.")
    youth_submissions = db.session.query(
        YouthArtistSubmission.id,
        YouthArtistSubmission.name,
        YouthArtistSubmission.age,
        YouthArtistSubmission.email,
        YouthArtistSubmission.about_why_design,
        YouthArtistSubmission.about_yourself,
        BadgeArtwork.artwork_file.label("artwork_file"),
        Badge.id.label("badge_id"),
        Badge.name.label("badge_name"),
    ).join(
        BadgeArtwork, BadgeArtwork.youth_submission_id == YouthArtistSubmission.id
    ).join(
        Badge, BadgeArtwork.badge_id == Badge.id
    ).distinct().all()
    logger.debug(f"Youth submissions retrieved: {len(youth_submissions)}")

    # Prepare youth submissions
    saved_youth_votes = db.session.query(JudgeVote).filter_by(user_id=user_id).order_by(JudgeVote.rank).all()
    ranked_youth_submission_ids = [vote.submission_id for vote in saved_youth_votes]

    if saved_youth_votes:
        logger.debug("Sorting youth submissions based on saved votes.")
        ranked_youth_submissions = [
            submission for submission in youth_submissions if submission.id in ranked_youth_submission_ids
        ]
        ranked_youth_submissions.sort(key=lambda s: ranked_youth_submission_ids.index(s.id))
        unranked_youth_submissions = [
            submission for submission in youth_submissions if submission.id not in ranked_youth_submission_ids
        ]
        prepared_youth_submissions = ranked_youth_submissions + unranked_youth_submissions
    else:
        logger.debug("No saved votes for youth submissions. Preparing random order.")
        if "random_youth_order" not in session:
            random_youth_order = [submission.id for submission in youth_submissions]
            import random
            random.shuffle(random_youth_order)
            session["random_youth_order"] = random_youth_order
        else:
            random_youth_order = session["random_youth_order"]

        prepared_youth_submissions = sorted(
            youth_submissions, key=lambda s: random_youth_order.index(s.id)
        )

    logger.debug("Rendering judges ballot template.")
    return render_template(
        "judges_ballot.html",
        artist_submissions=prepared_artist_submissions,
        youth_submissions=prepared_youth_submissions,
        rank_form=rank_form,
        logout_form=logout_form
    )

@main_bp.route("/call_for_artists", methods=["GET", "POST"])
def call_for_artists():
    application_root = current_app.config.get("APPLICATION_ROOT", "/")
    logger.debug("Accessing 'call_for_artists' route.")

    submission_open = is_submission_open()
    logger.debug(f"Submission open status: {submission_open}")

    is_admin = getattr(current_user, 'is_admin', False)
    logger.debug(f"Current user admin status: {is_admin}")

    submission_status = "Open" if submission_open else "Closed"
    logger.debug(f"Submission status: {submission_status}")

    submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()
    if submission_period:
        logger.debug(f"Submission period found: {submission_period}")
        submission_deadline = submission_period.submission_end.strftime("%B %d, %Y at %I:%M %p %Z")
    else:
        logger.warning("No submission period found in database.")
        submission_deadline = "N/A"

    form = ArtistSubmissionForm()
    logger.debug("ArtistSubmissionForm initialized.")

    badges = Badge.query.all()
    logger.debug(f"Retrieved {len(badges)} badges from the database.")

    badge_choices = [(str(badge.id), f"{badge.name}: {badge.description}") for badge in badges]
    for badge_upload in form.badge_uploads.entries:
        badge_upload.form.badge_id.choices = badge_choices
    logger.debug("Badge choices populated in form.")

    if request.method == "POST":
        logger.debug("POST request received.")
        if not submission_open and not is_admin:
            logger.warning("Submission attempt while submissions are closed.")
            flash("Submissions are currently closed. You cannot submit at this time.", "danger")
            return redirect(url_for("main.call_for_artists"))

        # Check if the email already exists
        email = form.email.data
        existing_submission = ArtistSubmission.query.filter_by(email=email).first()
        if existing_submission:
            flash("The provided email is already associated with an existing submission. Please use a different email.", "danger")
            return render_template(
                "call_for_artists.html",
                form=form,
                badges=badges,
                submission_open=submission_open,
                submission_status=submission_status,
                submission_deadline=submission_deadline,
                is_admin=is_admin
            )

        try:
            # Process each badge upload entry
            for badge_upload in form.badge_uploads.entries:
                badge_id = badge_upload.form.badge_id.data
                artwork_file = badge_upload.form.artwork_file.data

                logger.debug(f"Badge ID: {badge_id}, Artwork File: {artwork_file}")

                # Check if a new file has been uploaded
                if not artwork_file or not hasattr(artwork_file, "filename") or not artwork_file.filename.strip():
                    # Attempt to use the cached file path
                    cached_file_path = badge_upload.form.cached_file_path.data  # Access the hidden field
                    if cached_file_path and os.path.exists(cached_file_path):
                        logger.debug(f"Using cached file for badge {badge_id}: {cached_file_path}")
                        continue  # No action needed; cached file is already associated
                    else:
                        flash("Missing artwork file. Please re-upload.", "danger")
                        return render_template(
                            "call_for_artists.html",
                            form=form,
                            badges=badges,
                            submission_open=submission_open,
                            submission_status=submission_status,
                            submission_deadline=submission_deadline,
                            is_admin=is_admin
                        )

                # Process the newly uploaded file
                if hasattr(artwork_file, "filename"):
                    file_ext = os.path.splitext(artwork_file.filename)[1].lower()
                    if file_ext not in ['.jpg', '.jpeg', '.png', '.svg']:
                        flash("Invalid file extension.", "danger")
                        return render_template(
                            "call_for_artists.html",
                            form=form,
                            badges=badges,
                            submission_open=submission_open,
                            submission_status=submission_status,
                            submission_deadline=submission_deadline,
                            is_admin=is_admin
                        )

                    unique_filename = f"{uuid.uuid4()}{file_ext}"
                    artwork_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_filename)
                    artwork_file.save(artwork_path)
                    logger.debug(f"File saved: {artwork_path}")
                    badge_upload.form.cached_file_path.data = artwork_path  # Update the cached_file_path

            # Validate the form after processing file uploads
            if not form.validate_on_submit():
                logger.debug("Form validation failed.")
                for field_name, errors in form.errors.items():
                    for error in errors:
                        logger.error(f"Validation error - {field_name}: {error}")
                        flash(f"{field_name}: {error}", "danger")
                return render_template(
                    "call_for_artists.html",
                    form=form,
                    badges=badges,
                    submission_open=submission_open,
                    submission_status=submission_status,
                    submission_deadline=submission_deadline,
                    is_admin=is_admin
                )

            # Save the main submission
            logger.debug("Form validated successfully. Processing submission.")
            submission = ArtistSubmission(
                name=form.name.data,
                email=form.email.data,
                phone_number=form.phone_number.data,
                artist_bio=form.artist_bio.data,
                portfolio_link=form.portfolio_link.data,
                statement=form.statement.data,
                demographic_identity=form.demographic_identity.data,
                lane_county_connection=form.lane_county_connection.data,
                hear_about_contest=form.hear_about_contest.data,
                future_engagement=form.future_engagement.data,
                consent_to_data=form.consent_to_data.data,
                opt_in_featured_artwork=form.opt_in_featured_artwork.data,
            )
            db.session.add(submission)
            db.session.flush()
            logger.debug(f"Submission added to database: {submission}")

            # Save badge artworks
            for badge_upload in form.badge_uploads.entries:
                badge_id = badge_upload.form.badge_id.data
                artwork_file = badge_upload.form.artwork_file.data

                # Find the highest current instance number for this badge and submission
                max_instance = db.session.query(db.func.max(BadgeArtwork.instance)).filter_by(submission_id=submission.id, badge_id=badge_id).scalar() or 0
                new_instance = max_instance + 1

                badge = Badge.query.get(int(badge_id))
                if not badge:
                    logger.error(f"Invalid badge ID: {badge_id}")
                    flash("Invalid badge selection.", "danger")
                    db.session.rollback()
                    return redirect(url_for("main.call_for_artists"))

                # Handle artwork file
                if badge_upload.form.cached_file_path.data:
                    unique_filename = os.path.basename(badge_upload.form.cached_file_path.data)
                else:
                    unique_filename = None  # Or handle accordingly

                # Save badge artwork
                badge_artwork = BadgeArtwork(
                    submission_id=submission.id,
                    badge_id=int(badge_id),
                    instance=new_instance,
                    artwork_file=unique_filename
                )
                db.session.add(badge_artwork)
                logger.debug(f"BadgeArtwork added: {badge_artwork}")

            db.session.commit()
            logger.info("Submission and badge artworks committed to database successfully.")
            flash("Submission received successfully!", "success")
            return redirect(
                url_for("main.submission_success", submission_id=submission.id, type="artist")
            )

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during submission process: {e}")
            logger.error(traceback.format_exc())

            flash("An error occurred while processing your submission. Please try again.", "danger")
            return render_template(
                "call_for_artists.html",
                form=form,
                badges=badges,
                submission_open=submission_open,
                submission_status=submission_status,
                submission_deadline=submission_deadline,
                is_admin=is_admin
            )

    # GET request
    return render_template(
        "call_for_artists.html",
        form=form,
        badges=badges,
        submission_open=submission_open,
        submission_status=submission_status,
        submission_deadline=submission_deadline,
        is_admin=is_admin,
        application_root=application_root,
        submission_period=submission_period  # Pass the submission period object
    )

@main_bp.route("/call_for_youth_artists", methods=["GET", "POST"])
def call_for_youth_artists():
    try:
        submission_open = is_submission_open()
        is_admin = getattr(current_user, 'is_admin', False)
        submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()

        submission_start = (
            submission_period.submission_start.strftime("%B %d, %Y at %I:%M %p %Z")
            if submission_period else "N/A"
        )
        submission_end = (
            submission_period.submission_end.strftime("%B %d, %Y at %I:%M %p %Z")
            if submission_period else "N/A"
        )

        form = YouthArtistSubmissionForm()
        badges = Badge.query.all()
        badge_choices = [(badge.id, badge.name) for badge in badges]
        form.badge_id.choices = badge_choices

        if request.method == "POST":
            if not submission_open and not is_admin:
                flash("Submissions are currently closed. You cannot submit at this time.", "danger")
                return redirect(url_for("main.call_for_youth_artists"))

            if not form.validate_on_submit():
                flash("Please correct the errors in the form.", "danger")
                return render_template(
                    "call_for_youth_artists.html",
                    form=form,
                    badges=badges,
                    submission_open=submission_open,
                    submission_start=submission_start,
                    submission_end=submission_end,
                    is_admin=is_admin,
                )

            email = form.email.data
            existing_submission = YouthArtistSubmission.query.filter_by(email=email).first()
            if existing_submission:
                flash("The provided email is already associated with an existing youth submission. Please use a different email.", "danger")
                return render_template(
                    "call_for_youth_artists.html",
                    form=form,
                    badges=badges,
                    submission_open=submission_open,
                    submission_start=submission_start,
                    submission_end=submission_end,
                    is_admin=is_admin,
                )

            badge_id = form.badge_id.data
            artwork_file = form.artwork_file.data

            if not badge_id or not artwork_file:
                flash("Please select a valid badge and upload the corresponding artwork.", "danger")
                return render_template(
                    "call_for_youth_artists.html",
                    form=form,
                    badges=badges,
                    submission_open=submission_open,
                    submission_start=submission_start,
                    submission_end=submission_end,
                    is_admin=is_admin,
                )

            if not Badge.query.get(badge_id):
                flash("Invalid badge selection.", "danger")
                return render_template(
                    "call_for_youth_artists.html",
                    form=form,
                    badges=badges,
                    submission_open=submission_open,
                    submission_start=submission_start,
                    submission_end=submission_end,
                    is_admin=is_admin,
                )

            file_ext = os.path.splitext(artwork_file.filename)[1]
            if file_ext.lower() not in ['.jpg', '.jpeg', '.png', '.svg']:
                flash("Invalid file format. Only JPG, JPEG, PNG, or SVG files are allowed.", "danger")
                return render_template(
                    "call_for_youth_artists.html",
                    form=form,
                    badges=badges,
                    submission_open=submission_open,
                    submission_start=submission_start,
                    submission_end=submission_end,
                    is_admin=is_admin,
                )

            unique_filename = f"{uuid.uuid4()}{file_ext}"
            artwork_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_filename)
            artwork_file.save(artwork_path)

            submission = YouthArtistSubmission(
                name=form.name.data,
                age=form.age.data,
                parent_contact_info=form.parent_contact_info.data,
                email=form.email.data,
                about_why_design=form.about_why_design.data,
                about_yourself=form.about_yourself.data,
                opt_in_featured_artwork=form.opt_in_featured_artwork.data,
                parent_consent=form.parent_consent.data
            )
            db.session.add(submission)
            db.session.flush()

            badge_artwork = BadgeArtwork(
                youth_submission_id=submission.id,
                badge_id=int(badge_id),
                artwork_file=unique_filename
            )
            db.session.add(badge_artwork)
            db.session.commit()

            flash("Submission received successfully!", "success")
            return redirect(url_for("main.submission_success", submission_id=submission.id, type="youth_artist"))

        return render_template(
            "call_for_youth_artists.html",
            form=form,
            badges=badges,
            submission_open=submission_open,
            submission_start=submission_start,
            submission_end=submission_end,
            is_admin=is_admin,
            submission_period=submission_period
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during youth artist submission: {e}", exc_info=True)
        flash("A critical error occurred. Please contact support.", "danger")
        return redirect(url_for("main.index"))



@main_bp.route("/submission-success")
def submission_success():
    submission_id = request.args.get("submission_id")
    submission_type = request.args.get("type")

    submission_details = None
    badge_artworks = []

    if submission_type == "artist":
        submission_details = ArtistSubmission.query.get(submission_id)
        if submission_details:
            badge_artworks = BadgeArtwork.query.filter_by(submission_id=submission_details.id).all()
    elif submission_type == "youth_artist":
        submission_details = YouthArtistSubmission.query.get(submission_id)
        if submission_details:
            badge_artworks = BadgeArtwork.query.filter_by(youth_submission_id=submission_details.id).all()

    return render_template(
        "submission_success.html",
        submission_details=submission_details,
        submission_type=submission_type,
        badge_artworks=badge_artworks,
    )



@main_bp.route("/judges/submission-success")
def judges_submission_success():
    return render_template("judges_submission_success.html")


@main_bp.route("/api/badges", methods=["GET"])
def api_badges():
    badges = Badge.query.all()

    return jsonify([
        {"id": badge.id, "name": badge.name, "description": badge.description}
        for badge in badges
    ])



@main_bp.route("/api/check-email", methods=["POST"])
def check_email():
    try:
        # Validate CSRF token
        csrf_token = request.headers.get("X-CSRFToken")
        validate_csrf(csrf_token)

        # Parse the JSON request body
        data = request.get_json()
        email = data.get("email")

        if not email:
            return jsonify({"error": "Email is required"}), 400

        # Check if the email exists in the database
        is_available = ArtistSubmission.query.filter_by(email=email).first() is None
        return jsonify({"isAvailable": is_available})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
