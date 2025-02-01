from flask import Blueprint, jsonify, render_template, flash, redirect, request, current_app,  send_file
from flask_login import login_required, current_user
from fpdf import FPDF
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
import io
import os

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
            ArtistSubmission.id.label("artist_id"),
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
            BadgeArtwork.id, ArtistSubmission.id, ArtistSubmission.name, Badge.name, BadgeArtwork.artwork_file
        ).order_by(
            func.coalesce(func.sum(JudgeVote.rank), 0)
        ).all()
        current_app.logger.debug(f"Regular results fetched: {results}")

        # Youth results query
        current_app.logger.debug("Fetching youth results data.")
        youth_results = db.session.query(
            YouthArtistSubmission.id.label("youth_submission_id"),
            YouthArtistSubmission.name.label("artist_name"),
            YouthArtistSubmission.age.label("age"),
            Badge.name.label("badge_name"),
            BadgeArtwork.id.label("badge_artwork_id"),
            BadgeArtwork.artwork_file.label("artwork_file"),
            func.coalesce(func.sum(JudgeVote.rank), 0).label("total_score")
        ).join(
            BadgeArtwork, BadgeArtwork.youth_submission_id == YouthArtistSubmission.id, isouter=True
        ).join(
            JudgeVote, BadgeArtwork.id == JudgeVote.badge_artwork_id, isouter=True
        ).join(
            Badge, Badge.id == BadgeArtwork.badge_id
        ).group_by(
            BadgeArtwork.id, YouthArtistSubmission.id, YouthArtistSubmission.name, YouthArtistSubmission.age, Badge.name, BadgeArtwork.artwork_file
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

        # Processing judge votes into dictionaries
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
        # In case of error, supply empty lists so that the template can render
        return render_template("judges_results.html", 
            error="An error occurred while loading the results page.",
            results=[],
            youth_results=[],
            judge_votes_by_artwork={},
            judge_votes_by_youth_submission={},
            judges_status={}
        ), 500



@admin_bp.route("/clear_votes", methods=["POST"])
@login_required
@admin_required  # Ensure only admins can access this route
def clear_votes():
    try:
        # Delete all JudgeVote records for all judges (both artist and youth)
        db.session.query(JudgeVote).delete()
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error clearing votes: {e}", exc_info=True)
        return jsonify({"error": "An error occurred while clearing votes."}), 500




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



@admin_bp.route("/api/artwork-detail/<submission_type>/<int:submission_id>", methods=["GET"])
@login_required
def api_artwork_detail(submission_type, submission_id):
    # Initialize variables
    submission = None
    badge_artwork = None

    if submission_type == "artist":
        # Attempt to find a BadgeArtwork by filtering on submission_id.
        badge_artwork = BadgeArtwork.query.options(
            joinedload(BadgeArtwork.submission)
        ).filter_by(submission_id=submission_id).first()
        if badge_artwork and badge_artwork.submission:
            submission = badge_artwork.submission
        else:
            # Fallback: directly look up the ArtistSubmission.
            submission = ArtistSubmission.query.get(submission_id)
            if submission and submission.badge_artworks:
                # Use the first associated BadgeArtwork for display.
                badge_artwork = submission.badge_artworks[0]

        if submission:
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
                "badge_artworks": []
            }
            if badge_artwork:
                artwork_details["badge_artworks"].append({
                    "badge_id": badge_artwork.badge_id,
                    "artwork_file": url_for('static',
                                              filename=f"submissions/{badge_artwork.artwork_file}",
                                              _external=True)
                })
            return jsonify(artwork_details)

    elif submission_type == "youth":
        # Attempt to find a BadgeArtwork by filtering on youth_submission_id.
        badge_artwork = BadgeArtwork.query.options(
            joinedload(BadgeArtwork.youth_submission)
        ).filter_by(youth_submission_id=submission_id).first()
        if badge_artwork and badge_artwork.youth_submission:
            submission = badge_artwork.youth_submission
        else:
            # Fallback: directly look up the YouthArtistSubmission.
            submission = YouthArtistSubmission.query.get(submission_id)
            if submission and submission.badge_artworks:
                badge_artwork = submission.badge_artworks[0]

        if submission:
            artwork_details = {
                "type": "youth",
                "name": submission.name,
                "email": submission.email,
                "age": submission.age,
                "parent_contact_info": submission.parent_contact_info,
                "about_why_design": submission.about_why_design,
                "about_yourself": submission.about_yourself,
                "opt_in_featured_artwork": submission.opt_in_featured_artwork,
                "parent_consent": submission.parent_consent,
                "badge_artworks": []
            }
            if badge_artwork:
                artwork_details["badge_artworks"].append({
                    "badge_id": badge_artwork.badge_id,
                    "artwork_file": url_for('static',
                                              filename=f"submissions/{badge_artwork.artwork_file}",
                                              _external=True)
                })
            return jsonify(artwork_details)

    # If no submission is found
    return jsonify({"error": "Item not found"}), 404


@admin_bp.route("/judges/ballot/delete/<submission_type>/<int:submission_id>", methods=["POST"])
@login_required
@admin_required
def delete_submission(submission_type, submission_id):
    if submission_type == "artist":
        submission = ArtistSubmission.query.get_or_404(submission_id)
    elif submission_type == "youth":
        submission = YouthArtistSubmission.query.get_or_404(submission_id)
    else:
        return jsonify({"error": "Invalid submission type."}), 400

    try:
        # Delete the submission; the related BadgeArtwork and JudgeVote records
        # will be automatically deleted due to the cascade rules defined in your models.
        db.session.delete(submission)
        db.session.commit()
        return jsonify({"success": "Submission deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting submission {submission_id}: {e}", exc_info=True)
        return jsonify({"error": "An error occurred while deleting the submission."}), 500


@admin_bp.route("/admin/download-submissions", methods=["GET"])
@login_required
@admin_required
def download_submissions():
    """
    Generate a PDF containing all adult and youth submissions with all model fields,
    including associated badge artwork records and displaying the artwork images.
    """
    try:
        # Query all submissions
        artist_submissions = ArtistSubmission.query.order_by(ArtistSubmission.created_at).all()
        youth_submissions = YouthArtistSubmission.query.order_by(YouthArtistSubmission.created_at).all()

        # Initialize PDF document
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # --- Cover Page ---
        pdf.add_page()
        pdf.set_font("Arial", "B", 20)
        pdf.cell(0, 10, "Submissions Report", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Total Adult Submissions: {len(artist_submissions)}", ln=True)
        pdf.cell(0, 10, f"Total Youth Submissions: {len(youth_submissions)}", ln=True)
        pdf.ln(10)

        # Helper function to add artwork images
        def add_artwork_image(image_file):
            """
            Insert the artwork image into the PDF if the image file exists.
            The image is expected to reside in the static/submissions folder.
            """
            image_path = os.path.join(current_app.root_path, "static", "submissions", image_file)
            if os.path.exists(image_path):
                try:
                    # Save current cursor position (optional adjustment)
                    x = pdf.get_x()
                    y = pdf.get_y()
                    # Insert image with a width of 50 mm; adjust height automatically
                    pdf.image(image_path, x=x, y=y, w=50)
                    # Move below the image (add some vertical space)
                    pdf.ln(55)
                except Exception as img_ex:
                    pdf.cell(0, 10, f"Error displaying image: {img_ex}", ln=True)
            else:
                pdf.cell(0, 10, "Artwork image not found.", ln=True)

        # --- Adult (General) Submissions ---
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "General (Adult) Submissions", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "", 12)
        
        if artist_submissions:
            for submission in artist_submissions:
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, f"Submission ID: {submission.id}", ln=True)
                pdf.set_font("Arial", "", 12)
                pdf.cell(0, 10, f"Created At: {submission.created_at}", ln=True)
                pdf.cell(0, 10, f"Name: {submission.name}", ln=True)
                pdf.cell(0, 10, f"Email: {submission.email}", ln=True)
                pdf.cell(0, 10, f"Phone Number: {submission.phone_number or 'N/A'}", ln=True)
                pdf.ln(2)
                pdf.multi_cell(0, 10, f"Artist Bio: {submission.artist_bio}")
                pdf.ln(1)
                pdf.multi_cell(0, 10, f"Statement: {submission.statement}")
                pdf.ln(1)
                pdf.cell(0, 10, f"Portfolio Link: {submission.portfolio_link or 'N/A'}", ln=True)
                pdf.ln(1)
                pdf.multi_cell(0, 10, f"Demographic Identity: {submission.demographic_identity or 'N/A'}")
                pdf.ln(1)
                pdf.multi_cell(0, 10, f"Lane County Connection: {submission.lane_county_connection or 'N/A'}")
                pdf.ln(1)
                pdf.multi_cell(0, 10, f"Hear About Contest: {submission.hear_about_contest or 'N/A'}")
                pdf.ln(1)
                pdf.multi_cell(0, 10, f"Future Engagement: {submission.future_engagement or 'N/A'}")
                pdf.ln(1)
                pdf.cell(0, 10, f"Consent to Data: {submission.consent_to_data}", ln=True)
                pdf.cell(0, 10, f"Opt-in Featured Artwork: {submission.opt_in_featured_artwork}", ln=True)
                pdf.ln(5)
                pdf.cell(0, 10, "Badge Artworks:", ln=True)
                pdf.ln(2)
                
                if submission.badge_artworks:
                    for artwork in submission.badge_artworks:
                        pdf.set_font("Arial", "B", 12)
                        # Include badge ID and badge name (if the badge relation is loaded)
                        badge_info = f"Badge ID: {artwork.badge_id}"
                        if hasattr(artwork, "badge") and artwork.badge is not None:
                            badge_info += f" - {artwork.badge.name}"
                        pdf.cell(0, 10, badge_info, ln=True)
                        pdf.set_font("Arial", "", 12)
                        pdf.cell(0, 10, f"Artwork File: {artwork.artwork_file}", ln=True)
                        pdf.cell(0, 10, f"Instance: {artwork.instance}", ln=True)
                        pdf.ln(2)
                        # Display the artwork image
                        add_artwork_image(artwork.artwork_file)
                        pdf.ln(5)
                else:
                    pdf.cell(0, 10, "No badge artworks associated with this submission.", ln=True)
                pdf.ln(10)
        else:
            pdf.cell(0, 10, "No general submissions found.", ln=True)

        # --- Youth Submissions ---
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Youth Submissions", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "", 12)
        
        if youth_submissions:
            for submission in youth_submissions:
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, f"Submission ID: {submission.id}", ln=True)
                pdf.set_font("Arial", "", 12)
                pdf.cell(0, 10, f"Created At: {submission.created_at}", ln=True)
                pdf.cell(0, 10, f"Name: {submission.name}", ln=True)
                pdf.cell(0, 10, f"Age: {submission.age}", ln=True)
                pdf.cell(0, 10, f"Email: {submission.email}", ln=True)
                pdf.ln(2)
                pdf.multi_cell(0, 10, f"Parent Contact Info: {submission.parent_contact_info}")
                pdf.ln(1)
                pdf.multi_cell(0, 10, f"About Why Design: {submission.about_why_design}")
                pdf.ln(1)
                pdf.multi_cell(0, 10, f"About Yourself: {submission.about_yourself}")
                pdf.ln(1)
                pdf.cell(0, 10, f"Opt-in Featured Artwork: {submission.opt_in_featured_artwork}", ln=True)
                pdf.cell(0, 10, f"Parent Consent: {submission.parent_consent}", ln=True)
                pdf.ln(5)
                pdf.cell(0, 10, "Badge Artworks:", ln=True)
                pdf.ln(2)
                if submission.badge_artworks:
                    for artwork in submission.badge_artworks:
                        pdf.set_font("Arial", "B", 12)
                        badge_info = f"Badge ID: {artwork.badge_id}"
                        if hasattr(artwork, "badge") and artwork.badge is not None:
                            badge_info += f" - {artwork.badge.name}"
                        pdf.cell(0, 10, badge_info, ln=True)
                        pdf.set_font("Arial", "", 12)
                        pdf.cell(0, 10, f"Artwork File: {artwork.artwork_file}", ln=True)
                        pdf.cell(0, 10, f"Instance: {artwork.instance}", ln=True)
                        pdf.ln(2)
                        add_artwork_image(artwork.artwork_file)
                        pdf.ln(5)
                else:
                    pdf.cell(0, 10, "No badge artworks associated with this submission.", ln=True)
                pdf.ln(10)
        else:
            pdf.cell(0, 10, "No youth submissions found.", ln=True)

        # Write the PDF output to a bytes buffer and return as a download
        pdf_string = pdf.output(dest="S")  # 'S' means output as a string
        pdf_bytes = pdf_string.encode("latin1")  # Encoding using latin1 is recommended for PDF output
        pdf_buffer = io.BytesIO(pdf_bytes)
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name="submissions_full.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        current_app.logger.error(f"Error generating submissions PDF: {e}", exc_info=True)
        return "An error occurred while generating the PDF.", 500
    

@admin_bp.route("/judges/ballot/delete_all", methods=["POST"])
@login_required
@admin_required
def delete_all_submissions():
    """
    Deletes all artist and youth submissions along with their associated BadgeArtwork and JudgeVote records.
    """
    try:
        # Delete all JudgeVote records (if not handled by cascading deletes)
        JudgeVote.query.delete()
        # Delete all BadgeArtwork records
        BadgeArtwork.query.delete()
        # Delete all Artist Submissions
        ArtistSubmission.query.delete()
        # Delete all Youth Submissions
        YouthArtistSubmission.query.delete()
        db.session.commit()
        return jsonify({"success": "All submissions deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting all submissions: {e}", exc_info=True)
        return jsonify({"error": "An error occurred while deleting all submissions."}), 500
