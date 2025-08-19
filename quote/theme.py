# theme.py (Flask version)
from flask import Blueprint, current_app, render_template_string, url_for

bp = Blueprint(
    "theme",
    __name__,
    static_folder="static",           # serves /theme/static/…
    static_url_path="/theme/static",  # final URL will be /theme/static/…
    template_folder="templates"
)

def init_fsi_theme(app):
    """
    Register the theme blueprint and a Jinja helper.
    Usage in templates: {{ fsi_theme() }}
    Or include the CSS link directly: <link rel="stylesheet" href="{{ url_for('theme.static', filename='fsi.css') }}">
    """
    app.register_blueprint(bp)

    @app.context_processor
    def _fsi_theme_helper():
        def fsi_theme():
            href = url_for("theme.static", filename="fsi.css")
            # returns a <link> tag you can include in base.html
            return render_template_string('<link rel="stylesheet" href="{{ href }}">', href=href)
        return {"fsi_theme": fsi_theme}
