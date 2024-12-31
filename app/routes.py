from flask import jsonify, render_template, request, redirect, url_for, flash, jsonify, session, abort
from app import app, db
from app.models import ArtistSubmission, Judge, JudgeVote, Badge, BadgeArtwork
from app.forms import ArtistSubmissionForm, PasswordForm, RankingForm
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import joinedload
from io import TextIOWrapper

import os
import uuid
import csv

@app.route("/")
def index():
    # Get submission status and deadlines
    submission_open = is_submission_open()
    submission_status = "Open" if submission_open else "Closed"
    submission_deadline = SUBMISSION_END.strftime("%B %d, %Y at %I:%M %p %Z")

    # Fetch all badges
    badges = Badge.query.all()

    return render_template(
        "index.html",
        submission_status=submission_status,
        submission_deadline=submission_deadline,
        badges=badges  # Pass badges to the template
    )



# Constants for the submission period (use PST timezone)
SUBMISSION_START = datetime(2024, 12, 28, 12, 11, 0, tzinfo=timezone(timedelta(hours=-8)))  # Feb 1, 2025, 00:00 PST
SUBMISSION_END = datetime(2025, 2, 28, 23, 59, 59, tzinfo=timezone(timedelta(hours=-8)))  # Feb 28, 2025, 23:59 PST


def is_submission_open():
    """Returns True if the current time is within the submission period."""
    now = datetime.now(timezone(timedelta(hours=-8)))  # Current time in PST
    return SUBMISSION_START <= now <= SUBMISSION_END


@app.route("/admin", methods=["GET", "POST"])
def admin_page():
    if not session.get("is_judge") or not session.get("is_admin"):
        flash("Unauthorized access. Admin privileges required.", "danger")
        return redirect(url_for("judges_password"))

    # Check the current submission status
    submission_open = is_submission_open()
    submission_status = "Open" if submission_open else "Closed"

    # Fetch all judges for display
    judges = Judge.query.all()

    if request.method == "POST":
        # Adding a new judge
        action = request.form.get("action")
        if action == "add":
            name = request.form.get("name")
            password = request.form.get("password")
            is_admin = request.form.get("is_admin") == "on"  # Checkbox for admin status

            # Check if the judge name is unique
            existing_judge = Judge.query.filter_by(name=name).first()
            if existing_judge:
                flash(f"Judge '{name}' already exists!", "danger")
            else:
                # Add new judge
                new_judge = Judge(name=name, is_admin=is_admin)
                new_judge.set_password(password)  # Hash the password and store it
                db.session.add(new_judge)
                db.session.commit()
                flash(f"Judge '{name}' added successfully!", "success")
        
        # Removing a judge
        elif action == "remove":
            judge_id = request.form.get("judge_id")
            judge_to_remove = Judge.query.get(judge_id)
            if judge_to_remove:
                if judge_to_remove.is_admin:
                    flash("You cannot remove the admin.", "danger")
                else:
                    db.session.delete(judge_to_remove)
                    db.session.commit()
                    flash(f"Judge '{judge_to_remove.name}' removed successfully!", "success")
            else:
                flash("Judge not found!", "danger")

    # Re-fetch judges after any updates
    judges = Judge.query.all()
    return render_template("admin.html", judges=judges, submission_status=submission_status)
@app.route("/call_to_artists", methods=["GET", "POST"])
def call_to_artists():
    submission_open = is_submission_open()
    submission_status = "Open" if submission_open else "Closed"
    submission_deadline = SUBMISSION_END.strftime("%B %d, %Y at %I:%M %p %Z")

    if not submission_open:
        flash("Submissions are currently closed.", "danger")
        return redirect(url_for("index"))

    form = ArtistSubmissionForm()

    # Populate badge choices for the `badge_id` field inside each `badge_upload` in the `FieldList`
    badges = Badge.query.all()
    badge_choices = [(badge.id, f"{badge.name}: {badge.description}") for badge in badges]

    # Initialize choices for each `badge_upload` in the `FieldList`
    for badge_upload in form.badge_uploads:
        badge_upload.badge_id.choices = badge_choices

    if request.method == "POST":
        # Retain previously selected badge IDs and uploaded artwork files
        previous_badge_data = []
        for badge_upload in form.badge_uploads.entries:
            badge_id = badge_upload.badge_id.data
            artwork_file = badge_upload.artwork_file.data
            previous_badge_data.append({
                "badge_id": badge_id,
                "artwork_file": artwork_file.filename if artwork_file else None
            })

        if not form.validate_on_submit():
            # Collect and flash specific validation errors
            for field_name, errors in form.errors.items():
                for error in errors:
                    flash(f"{field_name}: {error}", "danger")

            # Render the template again with previous badge data
            return render_template(
                "call_to_artists.html",
                form=form,
                badges=badges,
                submission_status=submission_status,
                submission_deadline=submission_deadline,
                previous_badge_data=previous_badge_data  # Pass previous data to template
            )
        else:
            try:
                # Process form data and save to the database
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

                # Extract badge_ids and artwork_files from the form
                badge_ids = [badge_upload.badge_id.data for badge_upload in form.badge_uploads.entries]
                artwork_files = [badge_upload.artwork_file.data for badge_upload in form.badge_uploads.entries]

                # Validate badge-artwork pairings
                if len(badge_ids) != len(artwork_files) or not badge_ids:
                    flash("Each badge must have an associated artwork file.", "danger")
                    return redirect(url_for("call_to_artists"))

                # Create submission record
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
                    opt_in_featured_artwork=opt_in_featured_artwork,
                )
                db.session.add(submission)
                db.session.flush()  # Flush to get the submission ID

                # Process badge-artwork pairs
                for badge_id, artwork_file in zip(badge_ids, artwork_files):
                    # Validate badge
                    if not Badge.query.get(int(badge_id)):
                        flash("Invalid badge selection.", "danger")
                        db.session.rollback()
                        return redirect(url_for("call_to_artists"))

                    file_ext = os.path.splitext(artwork_file.filename)[1]
                    if not file_ext:
                        flash(f"Invalid file extension for uploaded file.", "danger")
                        db.session.rollback()
                        return redirect(url_for("call_to_artists"))

                    unique_filename = f"{uuid.uuid4()}{file_ext}"
                    artwork_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                    artwork_file.save(artwork_path)

                    badge_artwork = BadgeArtwork(
                        submission_id=submission.id,
                        badge_id=int(badge_id),
                        artwork_file=unique_filename
                    )
                    db.session.add(badge_artwork)

                db.session.commit()  # Commit all changes
                flash("Submission received successfully!", "success")
                return redirect(url_for("submission_success"))

            except Exception as e:
                db.session.rollback()
                flash("An error occurred while processing your submission. Please try again.", "danger")
                app.logger.error(f"Error processing submission: {e}")

    return render_template(
        "call_to_artists.html",
        form=form,
        badges=badges,
        submission_status=submission_status,
        submission_deadline=submission_deadline
    )


@app.route("/youth-artists")
def youth_artists():
    return render_template("youth_artists.html")

@app.route("/submission-success")
def submission_success():
    return render_template("submission_success.html")

@app.route("/carousel-images", methods=["GET"])
def carousel_images():
    # Get all files in the `static/submissions` folder
    submissions_folder = app.config["UPLOAD_FOLDER"]
    try:
        images = os.listdir(submissions_folder)
        # Generate URLs for the images (relative to "static/")
        image_urls = [f"static/submissions/{image}" for image in images]
        return jsonify(image_urls)
    except Exception as e:
        print(f"Error fetching images: {e}")
        return jsonify([])  # Return an empty list if there's an error


@app.route("/judges", methods=["GET"])
def judges_password():
    form = PasswordForm()

    # Check if an admin exists
    admin_exists = Judge.query.filter_by(is_admin=True).first()
    if not admin_exists:
        flash("No admin exists. The first password entered will create the admin.", "info")

    return render_template("judges_password.html", form=form)


@app.route("/judges/validate", methods=["POST"])
def validate_judge_password():
    form = PasswordForm()
    if form.validate_on_submit():
        password = form.password.data

        # Check if an admin already exists in the database
        admin_exists = Judge.query.filter_by(is_admin=True).first()

        # If no admin exists, create the first admin dynamically
        if not admin_exists:
            # Create the first admin with hashed password
            new_admin = Judge(name="admin", is_admin=True)
            new_admin.set_password(password)  # Hash and store the password
            db.session.add(new_admin)
            db.session.commit()

            # Set session variables for the newly created admin
            session["is_judge"] = True
            session["judge_id"] = new_admin.id
            session["is_admin"] = True

            flash(f"'{new_admin.name}' has been created as the first admin.", "success")
            return redirect(url_for("admin_page"))

        # Check if the password matches any existing judge
        judge = Judge.query.all()
        for existing_judge in judge:
            if check_password_hash(existing_judge.password_hash, password):
                # Valid judge login
                session["is_judge"] = True
                session["judge_id"] = existing_judge.id
                session["is_admin"] = existing_judge.is_admin

                if existing_judge.is_admin:
                    # Redirect to admin page if the judge is an admin
                    return redirect(url_for("admin_page"))
                else:
                    # Redirect to judge ballot otherwise
                    return redirect(url_for("judges_ballot"))

        # If no matching judge is found, reject the login attempt
        flash("Invalid password. Please try again.", "danger")
        return redirect(url_for("judges_password"))

    flash("Form validation failed. Please try again.", "danger")
    return redirect(url_for("judges_password"))


@app.route("/judges/ballot", methods=["GET", "POST"])
def judges_ballot():
    if not session.get("is_judge"):
        flash("Unauthorized access. Please log in.", "danger")
        return redirect(url_for("judges_password"))

    judge_id = session.get("judge_id")
    if not isinstance(judge_id, int):
        flash("Invalid session data. Please log in again.", "danger")
        return redirect(url_for("judges_password"))

    # Fetch all artist submissions
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
    ).distinct().all()  # Eliminate duplicates with DISTINCT

    # Retrieve existing votes for the current judge
    saved_votes = db.session.query(JudgeVote).filter_by(judge_id=judge_id).order_by(JudgeVote.rank).all()
    ranked_submission_ids = [vote.submission_id for vote in saved_votes]

    # Sort submissions: ranked first, unranked later
    ranked_submissions = [
        submission for submission in artist_submissions if submission.id in ranked_submission_ids
    ]
    ranked_submissions.sort(key=lambda s: ranked_submission_ids.index(s.id))

    unranked_submissions = [
        submission for submission in artist_submissions if submission.id not in ranked_submission_ids
    ]

    prepared_submissions = ranked_submissions + unranked_submissions

    # CSRF form
    form = RankingForm()

    # Save rankings when submitted
    if request.method == "POST":
        ranked_votes = request.form.get("rank", "")
        if ranked_votes:
            ranked_votes = ranked_votes.split(",")  # Convert to a list of submission IDs
            rank = 1  # Initialize rank counter manually
            try:
                with db.session.begin_nested():
                    # Clear existing votes for this judge
                    JudgeVote.query.filter_by(judge_id=judge_id).delete()

                    # Save new rankings
                    for submission_id in ranked_votes:
                        # Fetch the corresponding BadgeArtwork for the submission_id
                        badge_artwork = BadgeArtwork.query.filter_by(submission_id=submission_id).first()
                        if not badge_artwork:
                            flash(f"No BadgeArtwork found for submission ID {submission_id}.", "danger")
                            return redirect(url_for("judges_ballot"))

                        # Create a new vote with badge_artwork_id
                        vote = JudgeVote(
                            judge_id=judge_id,
                            submission_id=int(submission_id),
                            rank=rank,
                            badge_artwork_id=badge_artwork.id  # Associate the vote with the correct badge_artwork_id
                        )
                        db.session.add(vote)
                        rank += 1  # Increment rank manually
                db.session.commit()
                # Redirect to the success page
                return redirect(url_for("judges_submission_success"))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error saving rankings: {e}")
                flash("An error occurred while saving your rankings. Please try again.", "danger")
                return redirect(url_for("judges_ballot"))

    return render_template("judges_ballot.html", artist_submissions=prepared_submissions, form=form)


@app.route("/judges/results", methods=["GET"])
def judges_results():
    from sqlalchemy import func

    # Aggregate scores for each artwork (BadgeArtwork)
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
        func.sum(JudgeVote.rank)  # Lower score = higher ranking
    ).all()

    # Fetch individual judge votes for each artwork
    judge_votes = db.session.query(
        JudgeVote.badge_artwork_id,
        Judge.name.label("judge_name"),
        JudgeVote.rank
    ).join(
        Judge, Judge.id == JudgeVote.judge_id
    ).all()

    # Organize judge votes by badge_artwork_id
    judge_votes_by_artwork = {}
    for vote in judge_votes:
        artwork_id = vote.badge_artwork_id
        if artwork_id not in judge_votes_by_artwork:
            judge_votes_by_artwork[artwork_id] = []
        judge_votes_by_artwork[artwork_id].append({
            "judge_name": vote.judge_name,
            "rank": vote.rank
        })

    # Fetch distinct judge IDs who have voted
    voted_judges_ids = db.session.query(JudgeVote.judge_id).distinct().all()
    voted_judges_ids = [judge_id[0] for judge_id in voted_judges_ids]  # Extract IDs from query result

    # Get the names of judges who have voted
    voted_judges = db.session.query(Judge.name).filter(Judge.id.in_(voted_judges_ids)).all()
    voted_judges = [judge[0] for judge in voted_judges]  # Extract names from query result

    # Fetch all judge names and determine who has not voted
    all_judges = db.session.query(Judge).all()
    judges_status = {
        "voted": voted_judges,
        "not_voted": [judge.name for judge in all_judges if judge.name not in voted_judges],
    }

    return render_template(
        "judges_results.html",
        results=results,
        judge_votes_by_artwork=judge_votes_by_artwork,
        judges_status=judges_status
    )


@app.route("/judges/submission-success")
def judges_submission_success():
    return render_template("judges_submission_success.html")


@app.route("/judges/ballot/delete/<int:submission_id>", methods=["POST"])
def delete_submission(submission_id):
    if not session.get("is_judge") or not session.get("is_admin"):
        return jsonify({"error": "Unauthorized access. Admin privileges required."}), 403

    # Fetch the submission to delete
    submission = ArtistSubmission.query.get_or_404(submission_id)

    try:
        # Delete associated BadgeArtwork entries
        BadgeArtwork.query.filter_by(submission_id=submission.id).delete()

        # Delete associated JudgeVote entries
        JudgeVote.query.filter_by(submission_id=submission.id).delete()

        # Delete the submission itself
        db.session.delete(submission)
        db.session.commit()
        return jsonify({"success": "Submission deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting submission {submission_id}: {e}")
        return jsonify({"error": "An error occurred while deleting the submission."}), 500


@app.route("/badge-list")
def badge_list():
    # Fetch all badges
    badges = Badge.query.all()

    # Render the badge list template
    return jsonify([{"id": badge.id, "name": badge.name, "description": badge.description} for badge in badges])


@app.route("/api/badges", methods=["GET"])
def api_badges():
    # Fetch all badges from the database
    badges = Badge.query.all()

    # Return badge data as JSON, including the 'id'
    return jsonify([
        {"id": badge.id, "name": badge.name, "description": badge.description}
        for badge in badges
    ])


@app.route("/admin/badges", methods=["GET", "POST"])
def manage_badges():
    if not session.get("is_judge") or not session.get("is_admin"):
        flash("Unauthorized access. Admin privileges required.", "danger")
        return redirect(url_for("judges_password"))

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            name = request.form.get("name")
            description = request.form.get("description")

            # Check if the badge name is unique
            existing_badge = Badge.query.filter_by(name=name).first()
            if existing_badge:
                flash(f"Badge '{name}' already exists!", "danger")
            else:
                # Add new badge
                new_badge = Badge(name=name, description=description)
                db.session.add(new_badge)
                db.session.commit()
                flash(f"Badge '{name}' added successfully!", "success")

        elif action == "edit":
            badge_id = request.form.get("badge_id")
            name = request.form.get("name")
            description = request.form.get("description")

            # Update badge
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

            # Delete badge
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
                return redirect(url_for("manage_badges"))

            # Parse and process CSV file
            try:
                csv_reader = csv.reader(TextIOWrapper(csv_file, encoding="utf-8"))
                header = next(csv_reader)  # Skip the header row

                if header != ["Badge Name", "Badge Description"]:
                    flash("Invalid CSV format. Ensure the headers are 'Badge Name' and 'Badge Description'.", "danger")
                    return redirect(url_for("manage_badges"))

                added_badges = []
                for row in csv_reader:
                    if len(row) != 2:
                        flash(f"Invalid row in CSV: {row}. Skipping...", "warning")
                        continue

                    name, description = row
                    if not name or not description:
                        flash(f"Missing data in row: {row}. Skipping...", "warning")
                        continue

                    # Check for existing badge
                    existing_badge = Badge.query.filter_by(name=name).first()
                    if existing_badge:
                        flash(f"Badge '{name}' already exists. Skipping...", "warning")
                        continue

                    # Add new badge
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


@app.route("/validate_email", methods=["POST"])
def validate_email():
    email = request.json.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    # Check if the email already exists in the database
    existing_submission = ArtistSubmission.query.filter_by(email=email).first()
    if existing_submission:
        return jsonify({"error": "Email is already in use"}), 409  # 409 Conflict
    return jsonify({"success": "Email is available"}), 200


@app.route("/manage_judges", methods=["GET", "POST"])
def manage_judges():
    if not session.get("is_judge") or not session.get("is_admin"):
        flash("Unauthorized access. Admin privileges required.", "danger")
        return redirect(url_for("judges_password"))

    # Fetch all judges for display
    judges = Judge.query.all()

    if request.method == "POST":
        action = request.form.get("action")

        # Adding a new judge
        if action == "add":
            name = request.form.get("name")
            password = request.form.get("password")
            is_admin = request.form.get("is_admin") == "on"  # Checkbox for admin status

            # Check if the judge name is unique
            existing_judge = Judge.query.filter_by(name=name).first()
            if existing_judge:
                flash(f"Judge '{name}' already exists!", "danger")
            else:
                # Add new judge
                new_judge = Judge(name=name, is_admin=is_admin)
                new_judge.set_password(password)  # Hash the password and store it
                db.session.add(new_judge)
                db.session.commit()
                flash(f"Judge '{name}' added successfully!", "success")

        # Removing a judge
        elif action == "remove":
            judge_id = request.form.get("judge_id")
            judge_to_remove = Judge.query.get(judge_id)
            if judge_to_remove:
                if judge_to_remove.is_admin:
                    flash("You cannot remove the admin.", "danger")
                else:
                    db.session.delete(judge_to_remove)
                    db.session.commit()
                    flash(f"Judge '{judge_to_remove.name}' removed successfully!", "success")
            else:
                flash("Judge not found!", "danger")

    # Re-fetch judges after any updates
    judges = Judge.query.all()
    return render_template("manage_judges.html", judges=judges)


@app.route("/api/artwork-detail/<int:item_id>", methods=["GET"])
def api_artwork_detail(item_id):
    # Attempt to fetch as BadgeArtwork first
    badge_artwork = BadgeArtwork.query.options(joinedload(BadgeArtwork.submission)).filter_by(id=item_id).first()
    if badge_artwork:
        # If found, return details specific to BadgeArtwork
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

    # If not a BadgeArtwork, attempt to fetch as ArtistSubmission
    submission = ArtistSubmission.query.options(joinedload(ArtistSubmission.badge_artworks)).filter_by(id=item_id).first()
    if submission:
        # If found, return details specific to ArtistSubmission
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

    # If neither is found, return an error
    return jsonify({"error": "Item not found"}), 404


@app.route("/admin/clear_votes", methods=["POST"])
def clear_votes():
    if not session.get("is_judge") or not session.get("is_admin"):
        return jsonify({"error": "Unauthorized access. Admin privileges required."}), 403

    try:
        # Delete all votes from the JudgeVote table
        db.session.query(JudgeVote).delete()
        db.session.commit()
        return jsonify({"success": "All judge votes have been cleared successfully."}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error clearing votes: {e}")
        return jsonify({"error": "An error occurred while clearing votes."}), 500
