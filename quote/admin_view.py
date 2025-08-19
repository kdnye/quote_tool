# admin_view_bp.py
# Flask refactor of Streamlit admin_view.py
# - Exposes /admin/quotes (HTML table) and /admin/quotes.csv (download)
# - Simple session guard (role == 'admin'); replace with your central decorator if available

from __future__ import annotations

from flask import Blueprint, render_template_string, session, redirect, url_for, flash, Response
from jinja2 import DictLoader
import io
import csv

from db import Session, Quote

admin_bp = Blueprint("admin_bp", __name__)

# ---------------- Templates ----------------
BASE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title or 'Admin' }}</title>
    <link rel=stylesheet href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <style>
      body, .container { background:#a0a0a0; color:#fff; }
      table th, table td { color:#fff; }
      .toolbar { display:flex; gap:.5rem; align-items:center; margin:1rem 0; }
      .right { margin-left:auto }
      .btn { background:#005B99; color:#fff; border-radius:6px; padding:.35rem .8rem; font-weight:600; text-decoration:none; }
      .btn:hover { background:#003366; }
    </style>
  </head>
  <body>
    <main class="container">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          {% for cat, msg in messages %}
            <article class="{{ 'secondary' if cat=='info' else '' }}">{{ msg }}</article>
          {% endfor %}
        {% endif %}
      {% endwith %}
      {% block content %}{% endblock %}
    </main>
  </body>
</html>
"""

ADMIN_QUOTES = """
{% extends 'base.html' %}
{% block content %}
  <h2>📦 All Submitted Quotes</h2>
  <div class="toolbar">
    <a class="btn" href="{{ url_for('admin_bp.quotes_csv') }}">Download CSV</a>
    <div class="right">
      <a class="btn" href="{{ url_for('quote_bp.quote') }}">Back to Quote</a>
    </div>
  </div>
  <table>
    <thead>
      <tr>
        <th>Quote ID</th><th>User ID</th><th>User Email</th><th>Type</th>
        <th>Origin</th><th>Destination</th><th>Weight</th><th>Method</th>
        <th>Zone</th><th>Total</th><th>Accessorials</th><th>Date</th>
      </tr>
    </thead>
    <tbody>
      {% for q in quotes %}
        <tr>
          <td>{{ q.quote_id }}</td>
          <td>{{ q.user_id }}</td>
          <td>{{ q.user_email }}</td>
          <td>{{ q.quote_type }}</td>
          <td>{{ q.origin }}</td>
          <td>{{ q.destination }}</td>
          <td>{{ '%.2f'|format(q.weight or 0) }}</td>
          <td>{{ q.weight_method }}</td>
          <td>{{ q.zone }}</td>
          <td>${{ '%.2f'|format(q.total or 0) }}</td>
          <td style="max-width:420px; white-space:pre-wrap;">{{ q.quote_metadata }}</td>
          <td>{{ q.created_at.strftime('%Y-%m-%d %H:%M') if q.created_at else '' }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}
"""

# Register inline templates if needed
from flask import current_app

def _ensure_templates():
    if not isinstance(current_app.jinja_loader, DictLoader):
        current_app.jinja_loader = DictLoader({})
    current_app.jinja_loader.mapping.setdefault('base.html', BASE)
    current_app.jinja_loader.mapping.setdefault('admin_quotes.html', ADMIN_QUOTES)

# ---------------- Routes ----------------

@admin_bp.route("/admin/quotes")
def quotes_html():
    if session.get("role") != "admin":
        flash("Admin login required.", "warning")
        return redirect(url_for("quote_bp.quote"))

    db = Session()
    quotes = db.query(Quote).all()
    db.close()

    _ensure_templates()
    return render_template_string(ADMIN_QUOTES, title="All Quotes", quotes=quotes)


@admin_bp.route("/admin/quotes.csv")
def quotes_csv():
    if session.get("role") != "admin":
        flash("Admin login required.", "warning")
        return redirect(url_for("quote_bp.quote"))

    db = Session()
    quotes = db.query(Quote).all()
    db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Quote ID","User ID","User Email","Type","Origin","Destination",
        "Weight","Method","Zone","Total","Accessorials","Date"
    ])
    for q in quotes:
        writer.writerow([
            q.quote_id,
            q.user_id,
            q.user_email,
            q.quote_type,
            q.origin,
            q.destination,
            q.weight,
            q.weight_method,
            q.zone,
            q.total,
            (q.quote_metadata or ""),
            q.created_at.strftime("%Y-%m-%d %H:%M") if getattr(q, 'created_at', None) else "",
        ])

    csv_bytes = output.getvalue().encode("utf-8")
    return Response(csv_bytes, headers={
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": "attachment; filename=quotes.csv",
    })

# --------- Usage ---------
# from admin_view_bp import admin_bp
# app.register_blueprint(admin_bp)
# Ensure session['role'] is set to 'admin' after login for access.
