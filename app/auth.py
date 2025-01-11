from flask import Blueprint, jsonify, render_template, flash, redirect, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.utils import custom_url_for as url_for
from app.forms import LoginForm, LogoutForm
from app.models import User, db
auth_bp = Blueprint('auth', __name__)


def login_judge(name, password, remember=False):
    judge = User.query.filter_by(name=name).first()

    if not judge:
        flash("Invalid username or password.", "danger")
        return None

    if not judge.check_password(password):
        flash("Invalid username or password.", "danger")
        return None

    login_user(judge, remember=remember, fresh=True)

    return url_for("admin.admin_page") if judge.is_admin else url_for("main.judges_ballot")


@auth_bp.route("/login", methods=["GET", "POST"])
def judges():
    current_app.logger.debug(f"User logged in: {current_user}")

    if current_user.is_authenticated:
        return redirect(url_for("admin.admin_page" if current_user.is_admin else "main.judges_ballot"))

    form = LoginForm()

    if form.validate_on_submit():
        name = form.name.data.strip()
        password = form.password.data.strip()
        remember = form.remember_me.data if hasattr(form, "remember_me") else False

        try:
            redirect_url = login_judge(name, password, remember)
            if redirect_url:
                return redirect(redirect_url)
        except Exception as e:
            db.session.rollback()
            flash("An error occurred during login. Please try again.", "danger")
            current_app.logger.error(f"Login Error: {e}")

    elif form.is_submitted():
        flash("Invalid form submission.", "danger")

    return render_template("judges.html", form=form)



@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    # Log out the user
    logout_user()
    session.clear()
    return redirect(url_for("main.index"))

