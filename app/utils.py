from flask import url_for as flask_url_for, current_app

def custom_url_for(endpoint, **values):
    """Custom url_for that prepends APPLICATION_ROOT."""
    application_root = current_app.config.get("APPLICATION_ROOT", "")
    original_url = flask_url_for(endpoint, **values)

    # Only prepend APPLICATION_ROOT if it's not already in the URL
    if not original_url.startswith(application_root):
        return f"{application_root}{original_url}"

    return original_url
