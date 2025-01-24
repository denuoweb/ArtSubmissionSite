from flask import Blueprint, jsonify, render_template, flash, redirect, request, current_app
from flask_login import login_required, current_user
from app.forms import LogoutForm, SubmissionDatesForm
from app.models import SubmissionPeriod, User, Badge, db, ArtistSubmission, BadgeArtwork, JudgeVote, YouthArtistSubmission
from app.utils import custom_url_for as url_for
from datetime import datetime, timezone
from io import TextIOWrapper
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from functools import wraps
from zoneinfo import ZoneInfo

import csv

admin_bp = Blueprint('admin', __name__)



def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            # Redirect to the login page if the user is not authenticated
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.judges"))
        if not current_user.is_admin:
            # Redirect to a non-privileged page if the user is not an admin
            flash("Unauthorized access. Admin privileges required.", "danger")
            return redirect(url_for("auth.judges"))
        # If authenticated and admin, allow access to the view
        return func(*args, **kwargs)
    return decorated_view


def is_submission_open():
    """Returns True if the current time is within the submission period."""
    now = datetime.now(timezone.utc)
    submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()
    if submission_period:
        return submission_period.submission_start <= now <= submission_period.submission_end
    return False


@admin_bp.route("/admin", methods=["GET", "POST"])
@login_required
@admin_required
def admin_page():
    logout_form = LogoutForm()

    submission_open = is_submission_open()
    submission_status = "Open" if submission_open else "Closed"
    judges = User.query.all()

    return render_template(
        "admin.html",
        judges=judges,
        submission_status=submission_status,
        logout_form=logout_form
    )


@admin_bp.route("/manage_judges", methods=["GET", "POST"])
@login_required
@admin_required
def manage_judges():
    judges = User.query.all()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            name = request.form.get("name")
            password = request.form.get("password")
            is_admin = request.form.get("is_admin") == "on"

            if User.query.filter_by(name=name).first():
                flash(f"User '{name}' already exists!", "danger")
            else:
                new_judge = User(name=name, is_admin=is_admin)
                new_judge.set_password(password)
                db.session.add(new_judge)
                db.session.commit()
                flash(f"User '{name}' added successfully!", "success")

        elif action == "remove":
            user_id = request.form.get("user_id")
            judge_to_remove = User.query.get(user_id)
            if judge_to_remove:
                if judge_to_remove.is_admin:
                    flash("Cannot remove the admin.", "danger")
                else:
                    db.session.delete(judge_to_remove)
                    db.session.commit()
                    flash(f"User '{judge_to_remove.name}' removed successfully!", "success")
            else:
                flash("User not found!", "danger")

    judges = User.query.all()
    return render_template("manage_judges.html", judges=judges)


@admin_bp.route("/admin/badges", methods=["GET", "POST"])
@login_required
@admin_required
def manage_badges():
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
                return redirect(url_for("admin.manage_badges"))

            try:
                csv_reader = csv.reader(TextIOWrapper(csv_file, encoding="utf-8"))
                header = next(csv_reader)

                if header != ["Badge Name", "Badge Description"]:
                    flash("Invalid CSV format. Ensure the headers are 'Badge Name' and 'Badge Description'.", "danger")
                    return redirect(url_for("admin.manage_badges"))

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


@admin_bp.route("/judges/results", methods=["GET"])
@login_required
@admin_required
def judges_results():
    current_app.logger.debug("Entered the judges_results route.")

    try:
        # Regular results query
        current_app.logger.debug("Fetching regular results data.")
        results = db.session.query(
            ArtistSubmission.name.label("artist_name"),
            Badge.name.label("badge_name"),
            BadgeArtwork.id.label("badge_artwork_id"),
            BadgeArtwork.artwork_file.label("artwork_file"),
            func.coalesce(func.sum(JudgeVote.rank), 0).label("total_score")
        ).join(
            BadgeArtwork, BadgeArtwork.id == JudgeVote.badge_artwork_id, isouter=True
        ).join(
            ArtistSubmission, ArtistSubmission.id == BadgeArtwork.submission_id
        ).join(
            Badge, Badge.id == BadgeArtwork.badge_id
        ).group_by(
            BadgeArtwork.id, ArtistSubmission.name, Badge.name, BadgeArtwork.artwork_file
        ).order_by(
            func.coalesce(func.sum(JudgeVote.rank), 0)
        ).all()
        current_app.logger.debug(f"Regular results fetched: {results}")

        # Youth results query
        current_app.logger.debug("Fetching youth results data.")
        youth_results = db.session.query(
            YouthArtistSubmission.name.label("artist_name"),
            YouthArtistSubmission.age.label("age"),
            Badge.name.label("badge_name"),
            YouthArtistSubmission.id.label("youth_artwork_id"),
            YouthArtistSubmission.artwork_file.label("artwork_file"),
            func.coalesce(func.sum(JudgeVote.rank), 0).label("total_score")
        ).join(
            JudgeVote, YouthArtistSubmission.id == JudgeVote.submission_id, isouter=True
        ).join(
            Badge, YouthArtistSubmission.badge_id == Badge.id
        ).group_by(
            YouthArtistSubmission.id, YouthArtistSubmission.name, YouthArtistSubmission.age, Badge.name, YouthArtistSubmission.artwork_file
        ).order_by(
            func.coalesce(func.sum(JudgeVote.rank), 0)
        ).all()
        current_app.logger.debug(f"Youth results fetched: {youth_results}")

        # Judge votes mapping
        current_app.logger.debug("Fetching judge votes.")
        judge_votes = db.session.query(
            JudgeVote.badge_artwork_id,
            User.name.label("judge_name"),
            JudgeVote.rank
        ).join(
            User, User.id == JudgeVote.user_id
        ).all()
        current_app.logger.debug(f"Judge votes fetched: {judge_votes}")

        youth_judge_votes = db.session.query(
            JudgeVote.submission_id.label("youth_submission_id"),
            User.name.label("judge_name"),
            JudgeVote.rank
        ).join(
            User, User.id == JudgeVote.user_id
        ).all()
        current_app.logger.debug(f"Youth judge votes fetched: {youth_judge_votes}")

        # Processing judge votes
        current_app.logger.debug("Processing judge votes into dictionaries.")
        judge_votes_by_artwork = {}
        for vote in judge_votes:
            artwork_id = vote.badge_artwork_id
            if artwork_id not in judge_votes_by_artwork:
                judge_votes_by_artwork[artwork_id] = []
            judge_votes_by_artwork[artwork_id].append({
                "judge_name": vote.judge_name,
                "rank": vote.rank
            })
        current_app.logger.debug(f"Judge votes by artwork: {judge_votes_by_artwork}")

        judge_votes_by_youth_submission = {}
        for vote in youth_judge_votes:
            submission_id = vote.youth_submission_id
            if submission_id not in judge_votes_by_youth_submission:
                judge_votes_by_youth_submission[submission_id] = []
            judge_votes_by_youth_submission[submission_id].append({
                "judge_name": vote.judge_name,
                "rank": vote.rank
            })
        current_app.logger.debug(f"Judge votes by youth submission: {judge_votes_by_youth_submission}")

        # Judges voting status
        current_app.logger.debug("Calculating judges voting status.")
        voted_judges = db.session.query(User.name).join(JudgeVote).distinct().all()
        voted_judges = [judge[0] for judge in voted_judges]
        current_app.logger.debug(f"Voted judges: {voted_judges}")

        all_judges = db.session.query(User.name).all()
        all_judge_names = [judge[0] for judge in all_judges]
        current_app.logger.debug(f"All judges: {all_judge_names}")

        judges_status = {
            "voted": voted_judges,
            "not_voted": [name for name in all_judge_names if name not in voted_judges],
        }
        current_app.logger.debug(f"Judges status calculated: {judges_status}")

        # Rendering the results template
        current_app.logger.debug("Rendering results page template.")
        return render_template(
            "judges_results.html",
            results=results,
            youth_results=youth_results,
            judge_votes_by_artwork=judge_votes_by_artwork,
            judge_votes_by_youth_submission=judge_votes_by_youth_submission,
            judges_status=judges_status
        )

    except Exception as e:
        current_app.logger.error(f"Error in judges_results route: {e}", exc_info=True)
        return render_template("error.html", error="An error occurred while loading the results page."), 500



@admin_bp.route("/admin/update-submission-dates", methods=["GET", "POST"])
@login_required
@admin_required
def update_submission_dates():
    try:
        submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()
    except Exception as e:
        current_app.logger.error(f"Error fetching submission period: {e}")
        flash("Database error: Unable to fetch submission period.", "danger")
        return redirect(url_for("admin.admin_page"))

    dates_form = SubmissionDatesForm(
        submission_start=submission_period.submission_start if submission_period else None,
        submission_end=submission_period.submission_end if submission_period else None,
    )

    if dates_form.validate_on_submit():
        try:
            pacific = ZoneInfo("US/Pacific")
            submission_start = dates_form.submission_start.data
            submission_end = dates_form.submission_end.data

            if not submission_start or not submission_end:
                flash("Both submission start and end dates are required.", "danger")
                return redirect(url_for("admin.update_submission_dates"))

            submission_start = submission_start.replace(tzinfo=pacific)
            submission_end = submission_end.replace(tzinfo=pacific)

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
            return redirect(url_for("admin.update_submission_dates"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating submission dates: {e}")
            flash("An error occurred while updating submission dates. Please try again.", "danger")

    return render_template("update_submission_dates.html", dates_form=dates_form)



@admin_bp.route("/api/artwork-detail/<int:item_id>", methods=["GET"])
@login_required
@admin_required
def api_artwork_detail(item_id):
    """
    Enhanced route to fetch submission details for either adult or youth.
    1) Try to look up as a BadgeArtwork
    2) Check if that references an adult or youth submission
    3) Fallback: directly look up an ArtistSubmission
    4) Fallback: directly look up a YouthArtistSubmission
    5) Return 404 if not found
    """
    # 1) Attempt to find a BadgeArtwork
    badge_artwork = BadgeArtwork.query.options(
        joinedload(BadgeArtwork.submission),    # Adult
        joinedload(BadgeArtwork.youth_submission)  # Youth
    ).filter_by(id=item_id).first()

    if badge_artwork:
        # Distinguish between adult or youth
        if badge_artwork.submission_id is not None and badge_artwork.submission:
            # Adult submission
            submission = badge_artwork.submission
            artwork_details = {
                "type": "adult",
                "name": submission.name,
                "email": submission.email,
                "artist_bio": submission.artist_bio,
                "portfolio_link": submission.portfolio_link,
                "statement": submission.statement,
                "demographic_identity": submission.demographic_identity,
                "lane_county_connection": submission.lane_county_connection,
                "hear_about_contest": submission.hear_about_contest,
                "future_engagement": submission.future_engagement,
                "opt_in_featured_artwork": submission.opt_in_featured_artwork,
                "badge_artworks": [
                    {
                        "badge_id": badge_artwork.badge_id,
                        "artwork_file": url_for('static',
                            filename=f"submissions/{badge_artwork.artwork_file}",
                            _external=True
                        ),
                    }
                ],
            }
            return jsonify(artwork_details)

    elif badge_artwork.youth_submission_id is not None and badge_artwork.youth_submission:
        # YOUTH submission
        youth_submission = badge_artwork.youth_submission
        artwork_details = {
            "type": "youth",
            "name": youth_submission.name,
            "email": youth_submission.email,
            "age": youth_submission.age,
            "parent_contact_info": youth_submission.parent_contact_info,
            "about_why_design": youth_submission.about_why_design,
            "about_yourself": youth_submission.about_yourself,
            "opt_in_featured_artwork": youth_submission.opt_in_featured_artwork,
            "parent_consent": youth_submission.parent_consent,
            "badge_artworks": [
                {
                    "badge_id": badge_artwork.badge_id,
                    "artwork_file": url_for('static',
                        filename=f"submissions/{badge_artwork.artwork_file}",
                        _external=True
                    ),
                }]
        }
        return jsonify(artwork_details)
    return jsonify({"error": "Item not found"}), 404


@admin_bp.route("/admin/clear_votes", methods=["POST"])
@login_required
@admin_required
def clear_votes():
    try:
        db.session.query(JudgeVote).delete()
        db.session.commit()
        return jsonify({"success": "All judge votes have been cleared successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "An error occurred while clearing votes."}), 500


@admin_bp.route("/judges/ballot/delete/<int:submission_id>", methods=["POST"])
@login_required
@admin_required
def delete_submission(submission_id):
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