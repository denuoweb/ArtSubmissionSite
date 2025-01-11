from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, session, abort, make_response, current_app
from flask_wtf.csrf import generate_csrf
from flask_login import login_required, current_user
from app.auth import judges_login
from app.admin import is_submission_open
from app.models import ArtistSubmission, YouthArtistSubmission, User, JudgeVote, Badge, BadgeArtwork, SubmissionPeriod, db
from app.forms import ArtistSubmissionForm, RankingForm, YouthArtistSubmissionForm, LogoutForm
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

import os
import uuid

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


@main_bp.route("/judges/ballot", methods=["GET", "POST"])
@login_required
def judges_ballot():
    if not current_user.is_authenticated:
        flash("Unauthorized access. Privileges required.", "danger")
        return redirect(url_for("main.index"))

    logout_form = LogoutForm()
    rank_form = RankingForm()

    if request.method == "POST" and rank_form.validate_on_submit():
        form_name = request.form.get("form_name")

        if form_name == "ranking_form":
            ranked_votes = request.form.get("rank", "")
            if ranked_votes:
                ranked_votes = ranked_votes.split(",")
                rank = 1
                try:
                    with db.session.begin_nested():
                        JudgeVote.query.filter_by(user_id=current_user.id).delete()

                        for submission_id in ranked_votes:
                            badge_artwork = BadgeArtwork.query.filter_by(submission_id=submission_id).first()
                            if not badge_artwork:
                                flash(f"No BadgeArtwork found for submission ID {submission_id}.", "danger")
                                return redirect(url_for("main.judges_ballot"))

                            vote = JudgeVote(
                                user_id=current_user.id,
                                submission_id=int(submission_id),
                                rank=rank,
                                badge_artwork_id=badge_artwork.id
                            )
                            db.session.add(vote)
                            rank += 1

                    db.session.commit()
                    flash("Rankings submitted successfully!", "success")
                except Exception as e:
                    db.session.rollback()
                    flash("An error occurred while saving rankings. Please try again.", "danger")
                return redirect(url_for("main.judges_submission_success"))

    # Retrieve submissions as in your original code
    user_id = current_user.id

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

    # Retrieve saved votes
    saved_votes = db.session.query(JudgeVote).filter_by(user_id=user_id).order_by(JudgeVote.rank).all()
    ranked_submission_ids = [vote.submission_id for vote in saved_votes]

    # Prepare submissions (ranked and unranked)
    if saved_votes:
        ranked_submissions = [
            submission for submission in artist_submissions if submission.id in ranked_submission_ids
        ]
        ranked_submissions.sort(key=lambda s: ranked_submission_ids.index(s.id))
        unranked_submissions = [
            submission for submission in artist_submissions if submission.id not in ranked_submission_ids
        ]
        prepared_artist_submissions = ranked_submissions + unranked_submissions
    else:
        import random
        random.shuffle(artist_submissions)
        prepared_artist_submissions = artist_submissions

    # Prepare youth submissions
    saved_youth_votes = db.session.query(JudgeVote).filter_by(user_id=user_id).order_by(JudgeVote.rank).all()
    ranked_youth_submission_ids = [vote.submission_id for vote in saved_youth_votes]

    if saved_youth_votes:
        ranked_youth_submissions = [
            submission for submission in youth_submissions if submission.id in ranked_youth_submission_ids
        ]
        ranked_youth_submissions.sort(key=lambda s: ranked_youth_submission_ids.index(s.id))
        unranked_youth_submissions = [
            submission for submission in youth_submissions if submission.id not in ranked_youth_submission_ids
        ]
        prepared_youth_submissions = ranked_youth_submissions + unranked_youth_submissions
    else:
        random.shuffle(youth_submissions)
        prepared_youth_submissions = youth_submissions

    return render_template(
        "judges_ballot.html",
        artist_submissions=prepared_artist_submissions,
        youth_submissions=prepared_youth_submissions,
        rank_form=rank_form,
        logout_form=logout_form
    )


@main_bp.route("/call_for_artists", methods=["GET", "POST"])
def call_for_artists():
    application_root = current_app.config["APPLICATION_ROOT"]
    
    submission_open = is_submission_open()
    is_admin = getattr(current_user, 'is_admin', False)  # Check if current_user has 'is_admin', default to False
    submission_status = "Open" if submission_open else "Closed"
    
    submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()
    submission_deadline = submission_period.submission_end.strftime("%B %d, %Y at %I:%M %p %Z") if submission_period else "N/A"

    form = ArtistSubmissionForm()

    badges = Badge.query.all()
    badge_choices = [(badge.id, f"{badge.name}: {badge.description}") for badge in badges]

    for badge_upload in form.badge_uploads:
        badge_upload.badge_id.choices = badge_choices

    previous_badge_data = []

    if request.method == "POST":
        if not submission_open and not is_admin:
            flash("Submissions are currently closed. You cannot submit at this time.", "danger")
            return redirect(url_for("main.call_for_artists"))

        for badge_upload in form.badge_uploads.entries:
            badge_id = badge_upload.badge_id.data
            artwork_file = badge_upload.artwork_file.data

            if hasattr(artwork_file, "filename"):
                filename = artwork_file.filename
            else:
                filename = artwork_file

            previous_badge_data.append({
                "badge_id": badge_id,
                "artwork_file": filename
            })

        if not form.validate_on_submit():
            for field_name, errors in form.errors.items():
                for error in errors:
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
        else:
            try:
                name = form.name.data
                email = form.email.data
                phone_number = form.phone_number.data
                artist_bio = form.artist_bio.data
                portfolio_link = form.portfolio_link.data
                statement = form.statement.data
                demographic_identity = form.demographic_identity.data
                lane_county_connection = form.lane_county_connection.data
                accessibility_needs = form.accessibility_needs.data
                future_engagement = form.future_engagement.data
                consent_to_data = form.consent_to_data.data
                opt_in_featured_artwork = form.opt_in_featured_artwork.data

                badge_ids = [badge_upload.badge_id.data for badge_upload in form.badge_uploads.entries]
                artwork_files = [badge_upload.artwork_file.data for badge_upload in form.badge_uploads.entries]

                if len(badge_ids) != len(artwork_files) or not badge_ids:
                    flash("Each badge must have an associated artwork file.", "danger")
                    return redirect(url_for("main.call_for_artists"))

                submission = ArtistSubmission(
                    name=name,
                    email=email,
                    phone_number=phone_number,
                    artist_bio=artist_bio,
                    portfolio_link=portfolio_link,
                    statement=statement,
                    demographic_identity=demographic_identity,
                    lane_county_connection=lane_county_connection,
                    accessibility_needs=accessibility_needs,
                    future_engagement=future_engagement,
                    consent_to_data=consent_to_data,
                    opt_in_featured_artwork=opt_in_featured_artwork
                )
                db.session.add(submission)
                db.session.flush()

                for badge_id, artwork_file in zip(badge_ids, artwork_files):
                    if not Badge.query.get(int(badge_id)):
                        flash("Invalid badge selection.", "danger")
                        db.session.rollback()
                        return redirect(url_for("main.call_for_artists"))

                    if hasattr(artwork_file, "filename"):
                        file_ext = os.path.splitext(artwork_file.filename)[1]
                        if not file_ext:
                            flash(f"Invalid file extension for uploaded file.", "danger")
                            db.session.rollback()
                            return redirect(url_for("main.call_for_artists"))

                        unique_filename = f"{uuid.uuid4()}{file_ext}"
                        artwork_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                        artwork_file.save(artwork_path)
                    else:
                        unique_filename = artwork_file

                    badge_artwork = BadgeArtwork(
                        submission_id=submission.id,
                        badge_id=int(badge_id),
                        artwork_file=unique_filename
                    )
                    db.session.add(badge_artwork)

                db.session.commit()
                flash("Submission received successfully!", "success")
                return redirect(url_for("main.submission_success"))

            except Exception as e:
                db.session.rollback()
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
    submission_open = is_submission_open()
    submission_status = "Open" if submission_open else "Closed"
    submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()
    submission_deadline = submission_period.submission_end.strftime("%B %d, %Y at %I:%M %p %Z") if submission_period else "N/A"

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
        else:
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
                artwork_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
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

