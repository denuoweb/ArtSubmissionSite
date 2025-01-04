from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import generate_csrf
from app.models import ArtistSubmission, YouthArtistSubmission, Judge, JudgeVote, Badge, BadgeArtwork, SubmissionPeriod, db
from app.forms import ArtistSubmissionForm, LoginForm, LogoutForm, RankingForm, YouthArtistSubmissionForm, SubmissionDatesForm
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import joinedload
from io import TextIOWrapper
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

import os
import uuid
import csv

main_bp = Blueprint('main', __name__)


def is_submission_open():
    """Returns True if the current time is within the submission period."""
    now = datetime.now(timezone.utc)
    submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()
    if submission_period:
        return submission_period.submission_start <= now <= submission_period.submission_end
    return False


@main_bp.route('/csrf-token', methods=['GET'])
def csrf_token():
    token = generate_csrf()
    return jsonify({'csrf_token': token})


@main_bp.route('/logout', methods=["POST"])
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('main.index'))


@main_bp.route("/")
def index():
    print(f"index() Current user: {current_user}")
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


@main_bp.route("/admin", methods=["GET", "POST"])
@login_required
def admin_page():
    print(f"admin() Current user: {current_user}")

    if not current_user.is_admin:
        flash("Unauthorized access. Admin privileges required.", "danger")
        return redirect(url_for("main.index"))

    # Initialize the logout form
    logout_form = LogoutForm()

    if logout_form.validate_on_submit():
        logout_user()
        session.clear()  # Clear session data to ensure user is fully logged out
        flash("You have been logged out.", "info")
        return redirect(url_for("main.judges_password"))

    submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()
    dates_form = SubmissionDatesForm(
        submission_start=submission_period.submission_start if submission_period else None,
        submission_end=submission_period.submission_end if submission_period else None,
    )
    if dates_form.validate_on_submit():
        try:
            pacific = ZoneInfo("US/Pacific")
            submission_start = dates_form.submission_start.data.replace(tzinfo=pacific)
            submission_end = dates_form.submission_end.data.replace(tzinfo=pacific)

            submission_start_utc = submission_start.astimezone(timezone.utc)
            submission_end_utc = submission_end.astimezone(timezone.utc)

            if submission_period:
                submission_period.submission_start = submission_start_utc
                submission_period.submission_end = submission_end_utc
            else:
                new_period = SubmissionPeriod(
                    submission_start=submission_start_utc,
                    submission_end=submission_end_utc,
                )
                db.session.add(new_period)

            db.session.commit()
            flash("Submission dates updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while updating submission dates. Please try again.", "danger")

    submission_open = is_submission_open()
    submission_status = "Open" if submission_open else "Closed"
    judges = Judge.query.all()

    return render_template(
        "admin.html",
        judges=judges,
        submission_status=submission_status,
        submission_start=submission_period.submission_start if submission_period else None,
        submission_end=submission_period.submission_end if submission_period else None,
        dates_form=dates_form,
        logout_form=logout_form
    )

@main_bp.route("/call_to_artists", methods=["GET", "POST"])
def call_to_artists():
    submission_open = is_submission_open()
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
        if not submission_open:
            flash("Submissions are currently closed. You cannot submit at this time.", "danger")
            return redirect(url_for("main.call_to_artists"))

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
                "call_to_artists.html",
                form=form,
                badges=badges,
                submission_open=submission_open,
                submission_status=submission_status,
                submission_deadline=submission_deadline,
                previous_badge_data=previous_badge_data
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
                    return redirect(url_for("main.call_to_artists"))

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
                        return redirect(url_for("main.call_to_artists"))

                    if hasattr(artwork_file, "filename"):
                        file_ext = os.path.splitext(artwork_file.filename)[1]
                        if not file_ext:
                            flash(f"Invalid file extension for uploaded file.", "danger")
                            db.session.rollback()
                            return redirect(url_for("main.call_to_artists"))

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
        "call_to_artists.html",
        form=form,
        badges=badges,
        submission_open=submission_open,
        submission_status=submission_status,
        submission_deadline=submission_deadline,
        previous_badge_data=previous_badge_data
    )


@main_bp.route("/call_to_youth_artists", methods=["GET", "POST"])
def call_to_youth_artists():
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
            return redirect(url_for("main.call_to_youth_artists"))

        if not form.validate_on_submit():
            for field_name, errors in form.errors.items():
                for error in errors:
                    flash(f"{field_name}: {error}", "danger")
            return render_template(
                "call_to_youth_artists.html",
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
                    return redirect(url_for("main.call_to_youth_artists"))

                if not Badge.query.get(badge_id):
                    flash("Invalid badge selection.", "danger")
                    return redirect(url_for("main.call_to_youth_artists"))

                file_ext = os.path.splitext(artwork_file.filename)[1]
                if not file_ext:
                    flash("Invalid file extension for uploaded file.", "danger")
                    return redirect(url_for("main.call_to_youth_artists"))

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
        "call_to_youth_artists.html",
        form=form,
        badges=badges,
        submission_open=submission_open,
        submission_status=submission_status,
        submission_deadline=submission_deadline,
    )

@main_bp.route("/submission-success")
def submission_success():
    return render_template("submission_success.html")


@main_bp.route("/judges", methods=["GET", "POST"])
def judges_password():
    print(f"judges_password() Current user: {current_user}")
    form = LoginForm()

    if current_user.is_authenticated:
        # Redirect based on user's role
        if current_user.is_admin:
            return redirect(url_for("main.admin_page"))
        else:
            return redirect(url_for("main.judges_ballot"))

    # Handle login form submission
    if form.validate_on_submit():
        name = form.name.data.strip()
        password = form.password.data.strip()

        try:
            # Check if any judges exist in the database
            judge_exists = Judge.query.first()

            if not judge_exists:
                # Create an admin judge account if no judges exist
                new_admin = Judge(name=name)
                new_admin.set_password(password)
                new_admin.is_admin = True
                db.session.add(new_admin)
                db.session.commit()
                login_user(new_admin)
                flash(f"Admin account created for {name}.", "success")
                return redirect(url_for("main.admin_page"))

            # Authenticate existing judge
            judge = Judge.query.filter_by(name=name).first()
            if judge and judge.check_password(password):
                login_user(judge)
                flash(f"Welcome, {judge.name}!", "success")
                # Redirect based on judge's admin status
                return redirect(url_for("main.admin_page") if judge.is_admin else url_for("main.judges_ballot"))
            else:
                flash("Invalid username or password.", "danger")

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error during login attempt: {str(e)}")
            flash("An error occurred. Please try again later.", "danger")
            return redirect(url_for("main.judges_password"))

    elif form.is_submitted():
        # Handles invalid form submissions
        flash("Invalid form submission. Please check your input.", "danger")

    return render_template('judges_password.html', form=form)
    

@main_bp.route("/judges/ballot", methods=["GET", "POST"])
@login_required
def judges_ballot():
    # Check if the user is logged in (handled by @login_required)
    if not current_user.is_authenticated:
        flash("Unauthorized access. Please log in.", "danger")
        return redirect(url_for("main.judges_password"))

    logout_form = LogoutForm()

    # Handle logout form submission
    if logout_form.validate_on_submit():
        logout_user()
        session.clear()  # Clear session data to ensure full logout
        flash("You have been logged out.", "info")
        return redirect(url_for("main.judges_password"))

    # Retrieve artist and youth submissions as in your original code
    judge_id = current_user.id

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
    saved_votes = db.session.query(JudgeVote).filter_by(judge_id=judge_id).order_by(JudgeVote.rank).all()
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
    saved_youth_votes = db.session.query(JudgeVote).filter_by(judge_id=judge_id).order_by(JudgeVote.rank).all()
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

    form = RankingForm()

    # Handle ranking form submission
    if request.method == "POST":
        ranked_votes = request.form.get("rank", "")
        if ranked_votes:
            ranked_votes = ranked_votes.split(",")
            rank = 1
            try:
                with db.session.begin_nested():
                    JudgeVote.query.filter_by(judge_id=judge_id).delete()

                    for submission_id in ranked_votes:
                        badge_artwork = BadgeArtwork.query.filter_by(submission_id=submission_id).first()
                        if not badge_artwork:
                            flash(f"No BadgeArtwork found for submission ID {submission_id}.", "danger")
                            return redirect(url_for("main.judges_ballot"))

                        vote = JudgeVote(
                            judge_id=judge_id,
                            submission_id=int(submission_id),
                            rank=rank,
                            badge_artwork_id=badge_artwork.id
                        )
                        db.session.add(vote)
                        rank += 1

                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash("An error occurred while saving artist rankings. Please try again.", "danger")
                return redirect(url_for("main.judges_ballot"))

        # Handle youth ranking similarly
        ranked_youth_votes = request.form.get("youth_rank", "")
        if ranked_youth_votes:
            ranked_youth_votes = ranked_youth_votes.split(",")
            rank = 1
            try:
                with db.session.begin_nested():
                    for submission_id in ranked_youth_votes:
                        vote = JudgeVote(
                            judge_id=judge_id,
                            submission_id=int(submission_id),
                            rank=rank
                        )
                        db.session.add(vote)
                        rank += 1

                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash("An error occurred while saving youth rankings. Please try again.", "danger")
                return redirect(url_for("main.judges_ballot"))

        return redirect(url_for("main.judges_submission_success"))

    return render_template(
        "judges_ballot.html",
        artist_submissions=prepared_artist_submissions,
        youth_submissions=prepared_youth_submissions,
        form=form,
        logout_form=logout_form
    )



@main_bp.route("/judges/results", methods=["GET"])
@login_required
def judges_results():
    if not current_user.is_admin:
        flash("Unauthorized access. Admin privileges required.", "danger")
        return redirect(url_for("main.index"))
    from sqlalchemy import func

    results = db.session.query(
        ArtistSubmission.name.label("artist_name"),
        Badge.name.label("badge_name"),
        BadgeArtwork.id.label("badge_artwork_id"),
        BadgeArtwork.artwork_file.label("artwork_file"),
        func.sum(JudgeVote.rank).label("total_score")
    ).join(
        BadgeArtwork, BadgeArtwork.id == JudgeVote.badge_artwork_id
    ).join(
        ArtistSubmission, ArtistSubmission.id == BadgeArtwork.submission_id
    ).join(
        Badge, Badge.id == BadgeArtwork.badge_id
    ).group_by(
        BadgeArtwork.id, ArtistSubmission.name, Badge.name, BadgeArtwork.artwork_file
    ).order_by(
        func.sum(JudgeVote.rank)
    ).all()

    youth_results = db.session.query(
        YouthArtistSubmission.name.label("artist_name"),
        YouthArtistSubmission.age.label("age"),
        Badge.name.label("badge_name"),
        YouthArtistSubmission.id.label("youth_artwork_id"),
        YouthArtistSubmission.artwork_file.label("artwork_file"),
        func.sum(JudgeVote.rank).label("total_score")
    ).join(
        JudgeVote, YouthArtistSubmission.id == JudgeVote.submission_id
    ).join(
        Badge, YouthArtistSubmission.badge_id == Badge.id
    ).group_by(
        YouthArtistSubmission.id, YouthArtistSubmission.name, YouthArtistSubmission.age, Badge.name, YouthArtistSubmission.artwork_file
    ).order_by(
        func.sum(JudgeVote.rank)
    ).all()

    judge_votes = db.session.query(
        JudgeVote.badge_artwork_id,
        Judge.name.label("judge_name"),
        JudgeVote.rank
    ).join(
        Judge, Judge.id == JudgeVote.judge_id
    ).all()

    youth_judge_votes = db.session.query(
        JudgeVote.submission_id.label("youth_submission_id"),
        Judge.name.label("judge_name"),
        JudgeVote.rank
    ).join(
        Judge, Judge.id == JudgeVote.judge_id
    ).all()

    judge_votes_by_artwork = {}
    for vote in judge_votes:
        artwork_id = vote.badge_artwork_id
        if artwork_id not in judge_votes_by_artwork:
            judge_votes_by_artwork[artwork_id] = []
        judge_votes_by_artwork[artwork_id].append({
            "judge_name": vote.judge_name,
            "rank": vote.rank
        })

    judge_votes_by_youth_submission = {}
    for vote in youth_judge_votes:
        submission_id = vote.youth_submission_id
        if submission_id not in judge_votes_by_youth_submission:
            judge_votes_by_youth_submission[submission_id] = []
        judge_votes_by_youth_submission[submission_id].append({
            "judge_name": vote.judge_name,
            "rank": vote.rank
        })

    voted_judges_ids = db.session.query(JudgeVote.judge_id).distinct().all()
    voted_judges_ids = [judge_id[0] for judge_id in voted_judges_ids]

    voted_judges = db.session.query(Judge.name).filter(Judge.id.in_(voted_judges_ids)).all()
    voted_judges = [judge[0] for judge in voted_judges]

    all_judges = db.session.query(Judge).all()
    judges_status = {
        "voted": voted_judges,
        "not_voted": [judge.name for judge in all_judges if judge.name not in voted_judges],
    }

    return render_template(
        "judges_results.html",
        results=results,
        youth_results=youth_results,
        judge_votes_by_artwork=judge_votes_by_artwork,
        judge_votes_by_youth_submission=judge_votes_by_youth_submission,
        judges_status=judges_status
    )


@main_bp.route("/judges/submission-success")
def judges_submission_success():
    return render_template("judges_submission_success.html")


@main_bp.route("/judges/ballot/delete/<int:submission_id>", methods=["POST"])
@login_required
def delete_submission(submission_id):
    if not current_user.is_admin:
        flash("Unauthorized access. Admin privileges required.", "danger")
        return redirect(url_for("main.index"))

    submission = ArtistSubmission.query.get_or_404(submission_id)

    try:
        BadgeArtwork.query.filter_by(submission_id=submission.id).delete()

        JudgeVote.query.filter_by(submission_id=submission.id).delete()

        db.session.delete(submission)
        db.session.commit()
        return jsonify({"success": "Submission deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting submission {submission_id}: {e}")
        return jsonify({"error": "An error occurred while deleting the submission."}), 500


@main_bp.route("/badge-list")
def badge_list():
    badges = Badge.query.all()

    return jsonify([{"id": badge.id, "name": badge.name, "description": badge.description} for badge in badges])


@main_bp.route("/api/badges", methods=["GET"])
def api_badges():
    badges = Badge.query.all()

    return jsonify([
        {"id": badge.id, "name": badge.name, "description": badge.description}
        for badge in badges
    ])


@main_bp.route("/admin/badges", methods=["GET", "POST"])
@login_required
def manage_badges():
    if not current_user.is_admin:
        flash("Unauthorized access. Admin privileges required.", "danger")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            name = request.form.get("name")
            description = request.form.get("description")

            existing_badge = Badge.query.filter_by(name=name).first()
            if existing_badge:
                flash(f"Badge '{name}' already exists!", "danger")
            else:
                new_badge = Badge(name=name, description=description)
                db.session.add(new_badge)
                db.session.commit()
                flash(f"Badge '{name}' added successfully!", "success")

        elif action == "edit":
            badge_id = request.form.get("badge_id")
            name = request.form.get("name")
            description = request.form.get("description")

            badge = Badge.query.get(badge_id)
            if badge:
                badge.name = name
                badge.description = description
                db.session.commit()
                flash(f"Badge '{name}' updated successfully!", "success")
            else:
                flash("Badge not found!", "danger")

        elif action == "delete":
            badge_id = request.form.get("badge_id")

            badge = Badge.query.get(badge_id)
            if badge:
                db.session.delete(badge)
                db.session.commit()
                flash(f"Badge '{badge.name}' deleted successfully!", "success")
            else:
                flash("Badge not found!", "danger")

        elif action == "upload_csv":
            csv_file = request.files.get("csv_file")
            if not csv_file or not csv_file.filename.endswith(".csv"):
                flash("Please upload a valid CSV file.", "danger")
                return redirect(url_for("main.manage_badges"))

            try:
                csv_reader = csv.reader(TextIOWrapper(csv_file, encoding="utf-8"))
                header = next(csv_reader)

                if header != ["Badge Name", "Badge Description"]:
                    flash("Invalid CSV format. Ensure the headers are 'Badge Name' and 'Badge Description'.", "danger")
                    return redirect(url_for("main.manage_badges"))

                added_badges = []
                for row in csv_reader:
                    if len(row) != 2:
                        flash(f"Invalid row in CSV: {row}. Skipping...", "warning")
                        continue

                    name, description = row
                    if not name or not description:
                        flash(f"Missing data in row: {row}. Skipping...", "warning")
                        continue

                    existing_badge = Badge.query.filter_by(name=name).first()
                    if existing_badge:
                        flash(f"Badge '{name}' already exists. Skipping...", "warning")
                        continue

                    new_badge = Badge(name=name, description=description)
                    db.session.add(new_badge)
                    added_badges.append(name)

                db.session.commit()
                if added_badges:
                    flash(f"Successfully added badges: {', '.join(added_badges)}.", "success")
                else:
                    flash("No new badges were added.", "warning")

            except Exception as e:
                db.session.rollback()
                flash(f"An error occurred while processing the CSV file: {e}", "danger")

    badges = Badge.query.all()
    return render_template("admin_badges.html", badges=badges)


@main_bp.route("/validate_email", methods=["POST"])
def validate_email():
    email = request.json.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    existing_submission = ArtistSubmission.query.filter_by(email=email).first()
    if existing_submission:
        return jsonify({"error": "Email is already in use"}), 409
    return jsonify({"success": "Email is available"}), 200


@main_bp.route("/manage_judges", methods=["GET", "POST"])
@login_required
def manage_judges():
    if not current_user.is_admin:
        flash("Unauthorized access. Admin privileges required.", "danger")
        return redirect(url_for("main.index"))

    judges = Judge.query.all()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            name = request.form.get("name")
            password = request.form.get("password")
            is_admin = request.form.get("is_admin") == "on"

            if Judge.query.filter_by(name=name).first():
                flash(f"Judge '{name}' already exists!", "danger")
            else:
                new_judge = Judge(name=name, is_admin=is_admin)
                new_judge.set_password(password)
                db.session.add(new_judge)
                db.session.commit()
                flash(f"Judge '{name}' added successfully!", "success")

        elif action == "remove":
            judge_id = request.form.get("judge_id")
            judge_to_remove = Judge.query.get(judge_id)
            if judge_to_remove:
                if judge_to_remove.is_admin:
                    flash("Cannot remove the admin.", "danger")
                else:
                    db.session.delete(judge_to_remove)
                    db.session.commit()
                    flash(f"Judge '{judge_to_remove.name}' removed successfully!", "success")
            else:
                flash("Judge not found!", "danger")

    judges = Judge.query.all()
    return render_template("manage_judges.html", judges=judges)


@main_bp.route("/api/artwork-detail/<int:item_id>", methods=["GET"])
@login_required
def api_artwork_detail(item_id):
    badge_artwork = BadgeArtwork.query.options(joinedload(BadgeArtwork.submission)).filter_by(id=item_id).first()
    if badge_artwork:
        submission = badge_artwork.submission
        artwork_details = {
            "name": submission.name,
            "email": submission.email,
            "artist_bio": submission.artist_bio,
            "portfolio_link": submission.portfolio_link,
            "statement": submission.statement,
            "demographic_identity": submission.demographic_identity,
            "lane_county_connection": submission.lane_county_connection,
            "accessibility_needs": submission.accessibility_needs,
            "future_engagement": submission.future_engagement,
            "badge_artworks": [
                {
                    "badge_id": badge_artwork.badge_id,
                    "artwork_file": url_for('static', filename=f"submissions/{badge_artwork.artwork_file}", _external=True)
                }
            ],
            "opt_in_featured_artwork": submission.opt_in_featured_artwork
        }
        return jsonify(artwork_details)

    submission = ArtistSubmission.query.options(joinedload(ArtistSubmission.badge_artworks)).filter_by(id=item_id).first()
    if submission:
        badge_artworks = [
            {
                "badge_id": artwork.badge_id,
                "artwork_file": url_for('static', filename=f"submissions/{artwork.artwork_file}", _external=True)
            } for artwork in submission.badge_artworks
        ]
        submission_details = {
            "name": submission.name,
            "email": submission.email,
            "artist_bio": submission.artist_bio,
            "portfolio_link": submission.portfolio_link,
            "statement": submission.statement,
            "demographic_identity": submission.demographic_identity,
            "lane_county_connection": submission.lane_county_connection,
            "accessibility_needs": submission.accessibility_needs,
            "future_engagement": submission.future_engagement,
            "badge_artworks": badge_artworks,
            "opt_in_featured_artwork": submission.opt_in_featured_artwork
        }
        return jsonify(submission_details)

    return jsonify({"error": "Item not found"}), 404


@main_bp.route("/admin/clear_votes", methods=["POST"])
@login_required
def clear_votes():
    if not current_user.is_admin:
        flash("Unauthorized access. Admin privileges required.", "danger")
        return redirect(url_for("main.index"))
    try:
        db.session.query(JudgeVote).delete()
        db.session.commit()
        return jsonify({"success": "All judge votes have been cleared successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "An error occurred while clearing votes."}), 500
