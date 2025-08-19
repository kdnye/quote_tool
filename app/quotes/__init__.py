from flask import Blueprint
quotes_bp = Blueprint("quotes", __name__, template_folder="../templates")
from . import routes  # noqa: E402
