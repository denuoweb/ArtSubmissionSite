from flask import Blueprint, jsonify, render_template, request, redirect, flash, session, abort, make_response, current_app
from flask_wtf.csrf import generate_csrf
from flask_login import login_required, current_user
from app.auth import judges_login
from app.admin import is_submission_open
from app.models import ArtistSubmission, YouthArtistSubmission, User, JudgeVote, Badge, BadgeArtwork, SubmissionPeriod, db
from app.forms import ArtistSubmissionForm, RankingForm, YouthArtistSubmissionForm, LogoutForm
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from app.utils import custom_url_for as url_for

import os
import uuid
import logging
import traceback

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


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
        YouthArtistSubmission.artwork_file.label("artwork_file"),
        Badge.id.label("badge_id"),
        Badge.name.label("badge_name"),
    ).join(
        Badge, YouthArtistSubmission.badge_id == Badge.id
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

    badge_choices = [(badge.id, f"{badge.name}: {badge.description}") for badge in badges]
    for badge_upload in form.badge_uploads.entries:
        badge_upload.badge_id.choices = badge_choices
    logger.debug("Badge choices populated in form.")

    previous_badge_data = []

    if request.method == "POST":
        logger.debug("POST request received.")
        if not submission_open and not is_admin:
            logger.warning("Submission attempt while submissions are closed.")
            flash("Submissions are currently closed. You cannot submit at this time.", "danger")
            return redirect(url_for("main.call_for_artists"))

        try:
            for badge_upload in form.badge_uploads.entries:
                badge_id = badge_upload.badge_id.data
                artwork_file = badge_upload.artwork_file.data

                filename = artwork_file.filename if hasattr(artwork_file, "filename") else artwork_file
                previous_badge_data.append({"badge_id": badge_id, "artwork_file": filename})
            logger.debug(f"Previous badge data: {previous_badge_data}")

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
                    previous_badge_data=previous_badge_data,
                    is_admin=is_admin
                )

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

            for badge_id, artwork_file in zip(
                [badge_upload.badge_id.data for badge_upload in form.badge_uploads.entries],
                [badge_upload.artwork_file.data for badge_upload in form.badge_uploads.entries]
            ):
                logger.debug(f"Processing badge ID {badge_id} with file {artwork_file}")
                badge = Badge.query.get(int(badge_id))
                if not badge:
                    logger.error(f"Invalid badge ID: {badge_id}")
                    flash("Invalid badge selection.", "danger")
                    db.session.rollback()
                    return redirect(url_for("main.call_for_artists"))

                if hasattr(artwork_file, "filename"):
                    file_ext = os.path.splitext(artwork_file.filename)[1]
                    if not file_ext:
                        logger.error(f"Invalid file extension for file: {artwork_file.filename}")
                        flash("Invalid file extension for uploaded file.", "danger")
                        db.session.rollback()
                        return redirect(url_for("main.call_for_artists"))

                    unique_filename = f"{uuid.uuid4()}{file_ext}"
                    artwork_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_filename)
                    artwork_file.save(artwork_path)
                    logger.debug(f"File saved to: {artwork_path}")
                else:
                    unique_filename = artwork_file
                    logger.debug("Artwork file is pre-uploaded or set directly in previous data.")

                badge_artwork = BadgeArtwork(
                    submission_id=submission.id,
                    badge_id=int(badge_id),
                    artwork_file=unique_filename
                )
                db.session.add(badge_artwork)
                logger.debug(f"BadgeArtwork added: {badge_artwork}")

            db.session.commit()
            logger.info("Submission and badge artworks committed to database successfully.")
            flash("Submission received successfully!", "success")
            return redirect(url_for("main.submission_success"))

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
        previous_badge_data=previous_badge_data,
        is_admin=is_admin,
        application_root=application_root
    )


@main_bp.route("/call_for_youth_artists", methods=["GET", "POST"])
def call_for_youth_artists():
    try:
        submission_open = is_submission_open()
        submission_status = "Open" if submission_open else "Closed"
        submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()
        submission_deadline = (
            submission_period.submission_end.strftime("%B %d, %Y at %I:%M %p %Z")
            if submission_period else "N/A"
        )


        form = YouthArtistSubmissionForm()

        badges = Badge.query.all()
        badge_choices = [(None, "Select a badge")] + [(badge.id, badge.name) for badge in badges]
        form.badge_id.choices = badge_choices

        if request.method == "POST":

            if not submission_open:
                flash("Submissions are currently closed. You cannot submit at this time.", "danger")
                return redirect(url_for("main.call_for_youth_artists"))

            if not form.validate_on_submit():
                for field_name, errors in form.errors.items():
                    for error in errors:
                        flash(f"{field_name}: {error}", "danger")
                return render_template(
                    "call_for_youth_artists.html",
                    form=form,
                    badges=badges,
                    submission_open=submission_open,
                    submission_status=submission_status,
                    submission_deadline=submission_deadline,
                )

            try:
                name = form.name.data
                age = form.age.data
                parent_contact_info = form.parent_contact_info.data
                email = form.email.data
                about_why_design = form.about_why_design.data
                about_yourself = form.about_yourself.data
                badge_id = form.badge_id.data
                artwork_file = form.artwork_file.data


                if badge_id is None:
                    flash("Please select a valid badge.", "danger")
                    return redirect(url_for("main.call_for_youth_artists"))

                if not Badge.query.get(badge_id):
                    flash("Invalid badge selection.", "danger")
                    return redirect(url_for("main.call_for_youth_artists"))

                file_ext = os.path.splitext(artwork_file.filename)[1]
                if not file_ext:
                    flash("Invalid file extension for uploaded file.", "danger")
                    return redirect(url_for("main.call_for_youth_artists"))

                unique_filename = f"{uuid.uuid4()}{file_ext}"
                artwork_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_filename)
                artwork_file.save(artwork_path)

                submission = YouthArtistSubmission(
                    name=name,
                    age=age,
                    parent_contact_info=parent_contact_info,
                    email=email,
                    about_why_design=about_why_design,
                    about_yourself=about_yourself,
                    badge_id=badge_id,
                    artwork_file=unique_filename
                )
                db.session.add(submission)
                db.session.commit()

                flash("Submission received successfully!", "success")
                return redirect(url_for("main.submission_success"))

            except Exception as e:
                db.session.rollback()
                flash("An error occurred while processing your submission. Please try again.", "danger")

        return render_template(
            "call_for_youth_artists.html",
            form=form,
            badges=badges,
            submission_open=submission_open,
            submission_status=submission_status,
            submission_deadline=submission_deadline,
        )
    except Exception as e:
        flash("A critical error occurred. Please contact support.", "danger")
        return redirect(url_for("main.index"))


@main_bp.route("/submission-success")
def submission_success():
    return render_template("submission_success.html")


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


@main_bp.route("/validate_email", methods=["POST"])
def validate_email():
    email = request.json.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    existing_submission = ArtistSubmission.query.filter_by(email=email).first()
    if existing_submission:
        return jsonify({"error": "Email is already in use"}), 409
    return jsonify({"success": "Email is available"}), 200

