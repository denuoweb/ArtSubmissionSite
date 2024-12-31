from flask import jsonify, render_template, request, redirect, url_for, flash, jsonify, session, abort
from app import app, db
from app.models import ArtistSubmission, YouthArtistSubmission, Judge, JudgeVote, Badge, BadgeArtwork, SubmissionPeriod
from app.forms import ArtistSubmissionForm, PasswordForm, RankingForm, YouthArtistSubmissionForm, SubmissionDatesForm
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import joinedload
from io import TextIOWrapper
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import os
import uuid
import csv


def is_submission_open():
    """Returns True if the current time is within the submission period."""
    now = datetime.now(timezone.utc)  # Current time in UTC
    submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()
    if submission_period:
        # Submission times are already stored in UTC, so no need for timezone assignment
        return submission_period.submission_start <= now <= submission_period.submission_end
    return False



@app.route("/")
def index():
    # Get submission status and deadlines
    submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()
    submission_open = is_submission_open()
    submission_status = "Open" if submission_open else "Closed"
    
    if submission_period:
        # Convert submission times to Pacific Time for display
        pacific = ZoneInfo("US/Pacific")
        submission_start = submission_period.submission_start.astimezone(pacific).strftime("%B %d, %Y at %I:%M %p %Z")
        submission_deadline = submission_period.submission_end.astimezone(pacific).strftime("%B %d, %Y at %I:%M %p %Z")
    else:
        submission_start = "N/A"
        submission_deadline = "N/A"

    # Fetch all badges
    badges = Badge.query.all()

    return render_template(
        "index.html",
        submission_status=submission_status,
        submission_start=submission_start,
        submission_deadline=submission_deadline,
        badges=badges  # Pass badges to the template
    )


@app.route("/admin", methods=["GET", "POST"])
def admin_page():
    if not session.get("is_judge") or not session.get("is_admin"):
        flash("Unauthorized access. Admin privileges required.", "danger")
        return redirect(url_for("judges_password"))

    # Fetch the latest submission period
    submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()

    # Pre-fill the form with existing dates if available
    dates_form = SubmissionDatesForm(
        submission_start=submission_period.submission_start if submission_period else None,
        submission_end=submission_period.submission_end if submission_period else None,
    )
    
    if dates_form.validate_on_submit():
        try:
            # Assign the local timezone (Pacific Time) to form data
            pacific = ZoneInfo("US/Pacific")
            submission_start = dates_form.submission_start.data.replace(tzinfo=pacific)
            submission_end = dates_form.submission_end.data.replace(tzinfo=pacific)

            # Convert the local time to UTC for storage
            submission_start_utc = submission_start.astimezone(timezone.utc)
            submission_end_utc = submission_end.astimezone(timezone.utc)

            if submission_period:
                # Update the existing submission period
                submission_period.submission_start = submission_start_utc
                submission_period.submission_end = submission_end_utc
            else:
                # Create a new submission period
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
            app.logger.error(f"Error updating submission dates: {e}")

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

    return render_template("admin.html",
        judges=judges,
        submission_status=submission_status,
        submission_start=submission_period.submission_start if submission_period else None,
        submission_end=submission_period.submission_end if submission_period else None,
        dates_form=dates_form)


@app.route("/call_to_artists", methods=["GET", "POST"])
def call_to_artists():
    submission_open = is_submission_open()
    submission_status = "Open" if submission_open else "Closed"
    submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()
    submission_deadline = submission_period.submission_end.strftime("%B %d, %Y at %I:%M %p %Z") if submission_period else "N/A"

    form = ArtistSubmissionForm()

    # Populate badge choices for the `badge_id` field inside each `badge_upload` in the `FieldList`
    badges = Badge.query.all()
    badge_choices = [(badge.id, f"{badge.name}: {badge.description}") for badge in badges]

    # Initialize choices for each `badge_upload` in the `FieldList`
    for badge_upload in form.badge_uploads:
        badge_upload.badge_id.choices = badge_choices

    previous_badge_data = []

    if request.method == "POST":
        if not submission_open:
            flash("Submissions are currently closed. You cannot submit at this time.", "danger")
            return redirect(url_for("call_to_artists"))

        for badge_upload in form.badge_uploads.entries:
            badge_id = badge_upload.badge_id.data
            artwork_file = badge_upload.artwork_file.data

            # Check if `artwork_file` is a FileStorage object or a string
            if hasattr(artwork_file, "filename"):  # FileStorage object
                filename = artwork_file.filename
            else:  # String (previously uploaded file name)
                filename = artwork_file

            previous_badge_data.append({
                "badge_id": badge_id,
                "artwork_file": filename
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
                submission_open=submission_open,
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
                    opt_in_featured_artwork=opt_in_featured_artwork
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

                    # If artwork_file is a string, it's an existing file; skip saving
                    if hasattr(artwork_file, "filename"):  # FileStorage object
                        file_ext = os.path.splitext(artwork_file.filename)[1]
                        if not file_ext:
                            flash(f"Invalid file extension for uploaded file.", "danger")
                            db.session.rollback()
                            return redirect(url_for("call_to_artists"))

                        unique_filename = f"{uuid.uuid4()}{file_ext}"
                        artwork_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                        artwork_file.save(artwork_path)
                    else:
                        # Use the previously uploaded file
                        unique_filename = artwork_file

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
        submission_open=submission_open,
        submission_status=submission_status,
        submission_deadline=submission_deadline,
        previous_badge_data=previous_badge_data  # Pass previous data to template
    )


@app.route("/call_to_youth_artists", methods=["GET", "POST"])
def call_to_youth_artists():
    submission_open = is_submission_open()
    submission_status = "Open" if submission_open else "Closed"
    submission_period = SubmissionPeriod.query.order_by(SubmissionPeriod.id.desc()).first()
    submission_deadline = submission_period.submission_end.strftime("%B %d, %Y at %I:%M %p %Z") if submission_period else "N/A"

    form = YouthArtistSubmissionForm()

    # Populate badge choices for the badge_id field
    badges = Badge.query.all()
    badge_choices = [(None, "Select a badge")] + [(badge.id, badge.name) for badge in badges]  # Use None for blank placeholder
    form.badge_id.choices = badge_choices

    if request.method == "POST":

        if not submission_open:
            flash("Submissions are currently closed. You cannot submit at this time.", "danger")
            return redirect(url_for("call_to_youth_artists"))

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
                # Extract form data
                name = form.name.data
                age = form.age.data
                parent_contact_info = form.parent_contact_info.data
                email = form.email.data
                about_why_design = form.about_why_design.data
                about_yourself = form.about_yourself.data
                badge_id = form.badge_id.data
                artwork_file = form.artwork_file.data

                # Validate badge selection
                if badge_id is None:  # The placeholder is selected
                    flash("Please select a valid badge.", "danger")
                    return redirect(url_for("call_to_youth_artists"))

                # Validate that the badge exists
                if not Badge.query.get(badge_id):
                    flash("Invalid badge selection.", "danger")
                    return redirect(url_for("call_to_youth_artists"))

                # Save the uploaded artwork file
                file_ext = os.path.splitext(artwork_file.filename)[1]
                if not file_ext:
                    flash("Invalid file extension for uploaded file.", "danger")
                    return redirect(url_for("call_to_youth_artists"))

                unique_filename = f"{uuid.uuid4()}{file_ext}"
                artwork_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                artwork_file.save(artwork_path)

                # Save submission to the database
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
                return redirect(url_for("submission_success"))

            except Exception as e:
                db.session.rollback()
                flash("An error occurred while processing your submission. Please try again.", "danger")
                app.logger.error(f"Error processing youth submission: {e}")

    return render_template(
        "call_to_youth_artists.html",
        form=form,
        badges=badges,
        submission_open=submission_open,
        submission_status=submission_status,
        submission_deadline=submission_deadline,
    )
    

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

    # Fetch all youth submissions
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

    # Prepare artist submissions
    saved_votes = db.session.query(JudgeVote).filter_by(judge_id=judge_id).order_by(JudgeVote.rank).all()
    ranked_submission_ids = [vote.submission_id for vote in saved_votes]

    if saved_votes:
        # If votes exist, use saved order
        ranked_submissions = [
            submission for submission in artist_submissions if submission.id in ranked_submission_ids
        ]
        ranked_submissions.sort(key=lambda s: ranked_submission_ids.index(s.id))
        unranked_submissions = [
            submission for submission in artist_submissions if submission.id not in ranked_submission_ids
        ]
        prepared_artist_submissions = ranked_submissions + unranked_submissions
    else:
        # If no votes exist, randomize submissions
        import random
        random.shuffle(artist_submissions)
        prepared_artist_submissions = artist_submissions

    # Prepare youth submissions (similar logic)
    saved_youth_votes = db.session.query(JudgeVote).filter_by(judge_id=judge_id).order_by(JudgeVote.rank).all()
    ranked_youth_submission_ids = [vote.submission_id for vote in saved_youth_votes]

    if saved_youth_votes:
        # If votes exist, use saved order
        ranked_youth_submissions = [
            submission for submission in youth_submissions if submission.id in ranked_youth_submission_ids
        ]
        ranked_youth_submissions.sort(key=lambda s: ranked_youth_submission_ids.index(s.id))
        unranked_youth_submissions = [
            submission for submission in youth_submissions if submission.id not in ranked_youth_submission_ids
        ]
        prepared_youth_submissions = ranked_youth_submissions + unranked_youth_submissions
    else:
        # If no votes exist, randomize youth submissions
        random.shuffle(youth_submissions)
        prepared_youth_submissions = youth_submissions

    # CSRF form
    form = RankingForm()

    # Save rankings when submitted
    if request.method == "POST":
        # Process rankings for regular artist submissions
        ranked_votes = request.form.get("rank", "")
        if ranked_votes:
            ranked_votes = ranked_votes.split(",")  # Convert to a list of submission IDs
            rank = 1
            try:
                with db.session.begin_nested():
                    # Clear existing votes for this judge
                    JudgeVote.query.filter_by(judge_id=judge_id).delete()

                    # Save new rankings for artist submissions
                    for submission_id in ranked_votes:
                        badge_artwork = BadgeArtwork.query.filter_by(submission_id=submission_id).first()
                        if not badge_artwork:
                            flash(f"No BadgeArtwork found for submission ID {submission_id}.", "danger")
                            return redirect(url_for("judges_ballot"))

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
                app.logger.error(f"Error saving artist rankings: {e}")
                flash("An error occurred while saving artist rankings. Please try again.", "danger")
                return redirect(url_for("judges_ballot"))

        # Process rankings for youth submissions
        ranked_youth_votes = request.form.get("youth_rank", "")
        if ranked_youth_votes:
            ranked_youth_votes = ranked_youth_votes.split(",")  # Convert to a list of submission IDs
            rank = 1
            try:
                with db.session.begin_nested():
                    # Save new rankings for youth submissions
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
                app.logger.error(f"Error saving youth rankings: {e}")
                flash("An error occurred while saving youth rankings. Please try again.", "danger")
                return redirect(url_for("judges_ballot"))

        return redirect(url_for("judges_submission_success"))

    return render_template(
        "judges_ballot.html",
        artist_submissions=prepared_artist_submissions,
        youth_submissions=prepared_youth_submissions,
        form=form
    )


@app.route("/judges/results", methods=["GET"])
def judges_results():
    from sqlalchemy import func

    # Aggregate scores for each artwork (BadgeArtwork) - General Submissions
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

    # Aggregate scores for Youth Submissions
    youth_results = db.session.query(
        YouthArtistSubmission.name.label("artist_name"),
        YouthArtistSubmission.age.label("age"),
        Badge.name.label("badge_name"),
        YouthArtistSubmission.id.label("youth_artwork_id"),
        YouthArtistSubmission.artwork_file.label("artwork_file"),
        func.sum(JudgeVote.rank).label("total_score")
    ).join(
        JudgeVote, YouthArtistSubmission.id == JudgeVote.submission_id  # Link JudgeVote to YouthArtistSubmission
    ).join(
        Badge, YouthArtistSubmission.badge_id == Badge.id
    ).group_by(
        YouthArtistSubmission.id, YouthArtistSubmission.name, YouthArtistSubmission.age, Badge.name, YouthArtistSubmission.artwork_file
    ).order_by(
        func.sum(JudgeVote.rank)  # Lower score = higher ranking
    ).all()

    # Fetch individual judge votes for each artwork - General Submissions
    judge_votes = db.session.query(
        JudgeVote.badge_artwork_id,
        Judge.name.label("judge_name"),
        JudgeVote.rank
    ).join(
        Judge, Judge.id == JudgeVote.judge_id
    ).all()

    # Fetch individual judge votes for youth submissions
    youth_judge_votes = db.session.query(
        JudgeVote.submission_id.label("youth_submission_id"),
        Judge.name.label("judge_name"),
        JudgeVote.rank
    ).join(
        Judge, Judge.id == JudgeVote.judge_id
    ).all()

    # Organize judge votes by badge_artwork_id (General Submissions)
    judge_votes_by_artwork = {}
    for vote in judge_votes:
        artwork_id = vote.badge_artwork_id
        if artwork_id not in judge_votes_by_artwork:
            judge_votes_by_artwork[artwork_id] = []
        judge_votes_by_artwork[artwork_id].append({
            "judge_name": vote.judge_name,
            "rank": vote.rank
        })

    # Organize judge votes by youth_submission_id
    judge_votes_by_youth_submission = {}
    for vote in youth_judge_votes:
        submission_id = vote.youth_submission_id
        if submission_id not in judge_votes_by_youth_submission:
            judge_votes_by_youth_submission[submission_id] = []
        judge_votes_by_youth_submission[submission_id].append({
            "judge_name": vote.judge_name,
            "rank": vote.rank
        })

    # Fetch distinct judge IDs who have voted
    voted_judges_ids = db.session.query(JudgeVote.judge_id).distinct().all()
    voted_judges_ids = [judge_id[0] for judge_id in voted_judges_ids]

    # Get the names of judges who have voted
    voted_judges = db.session.query(Judge.name).filter(Judge.id.in_(voted_judges_ids)).all()
    voted_judges = [judge[0] for judge in voted_judges]

    # Fetch all judge names and determine who has not voted
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
