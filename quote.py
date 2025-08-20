# quote_blueprint.py
# Flask refactor of the provided Streamlit quote module.
# - Provides /quote (GET/POST) and /admin/quotes (GET) routes
# - Mirrors calculations for Hotshot and Air
# - Persists to DB using db.Session and db.Quote
# - Loads workbook at Config.WORKBOOK_PATH

from flask import Blueprint, render_template_string, request, session, redirect, url_for, flash
from datetime import datetime
import os
import pandas as pd
import requests

# External deps expected from your project
from db import Session, Quote
from config import Config

quote_bp = Blueprint("quote_bp", __name__)


@quote_bp.teardown_request
def remove_session(exception=None):
    """Ensure scoped sessions are removed after each request."""
    if hasattr(Session, "remove"):
        Session.remove()

# ---------- Helpers ----------

def get_distance_miles(origin_zip: str, destination_zip: str):
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None
    url = (
        "https://maps.googleapis.com/maps/api/directions/json?"
        f"origin={origin_zip}&destination={destination_zip}&mode=driving&key={api_key}"
    )
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        if data.get("status") == "OK":
            meters = data["routes"][0]["legs"][0]["distance"]["value"]
            return meters / 1609.344
    except Exception:
        return None
    return None

# ---------- Inline templates (use real files if preferred) ----------

BASE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title or 'Quote Tool' }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css" />
    <style>
      body, .container { background:#a0a0a0; color:#fff; }
      header.nav { display:flex; gap:1rem; align-items:center; margin:1rem 0; }
      .right { margin-left:auto; display:flex; gap:.5rem; }
      .badge { padding:.15rem .5rem; border-radius:.5rem; background:#003366; }
      .btn-primary { background:#005B99; color:#fff; border-radius:6px; font-weight:600; }
      .btn-primary:hover { background:#003366; }
      .callout { background:#003366; padding: .75rem 1rem; border-radius:.5rem; }
      .muted { opacity:.85; }
      .grid-2 { display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }
      .stack { display:flex; flex-direction:column; gap:.5rem; }
      table td, table th { color:#fff; }
      .fsi-logo { height:56px; }
    </style>
  </head>
  <body>
    <nav class="container">
      <header class="nav">
        <a href="{{ url_for('quote_bp.quote') }}" class="contrast" style="display:flex;align-items:center;gap:.5rem;">
          <img class="fsi-logo" src="{{ url_for('static', filename='FSI-logo.png') }}" alt="FSI" />
          <strong>Quote Tool</strong>
        </a>
        <div class="right">
          <a role="button" class="btn-primary" href="{{ url_for('quote_bp.quote') }}">Get Quote</a>
          {% if session.get('role') == 'admin' %}
            <span class="badge">Admin: {{ session.get('name','') }}</span>
            <a role="button" href="{{ url_for('quote_bp.admin_quotes') }}">View Quotes</a>
          {% endif %}
        </div>
      </header>
    </nav>

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

QUOTE_FORM = """
{% extends 'base.html' %}
{% block content %}
  <h2>📦 Quote Tool</h2>
  <form method="post" action="{{ url_for('quote_bp.quote') }}">
    <fieldset>
      <label>Quote Type
        <select name="quote_mode">
          <option value="Hotshot" {{ 'selected' if quote_mode=='Hotshot' else '' }}>Hotshot</option>
          <option value="Air" {{ 'selected' if quote_mode=='Air' else '' }}>Air</option>
        </select>
      </label>
    </fieldset>

    <div class="grid-2">
      <div class="stack">
        <label>Origin Zip <input name="origin" value="{{ origin or '' }}" required /></label>
        <label>Destination Zip <input name="destination" value="{{ destination or '' }}" required /></label>

        <h4>📦 Weight Entry</h4>
        <label>Weight Method
          <select name="weight_input_method" onchange="this.form.submit()">
            <option {{ 'selected' if weight_input_method=='Actual Weight' else '' }}>Actual Weight</option>
            <option {{ 'selected' if weight_input_method=='Dimensional Weight' else '' }}>Dimensional Weight</option>
          </select>
        </label>

        {% if weight_input_method == 'Actual Weight' %}
          <label>Actual Weight (lbs) <input type="number" name="weight" step="1" min="1" value="{{ weight or '' }}" required></label>
        {% else %}
          <p><strong>Enter package dimensions (inches):</strong></p>
          <label>Length <input type="number" name="length" step="1" min="1" value="{{ length or '' }}" required></label>
          <label>Width <input type="number" name="width" step="1" min="1" value="{{ width or '' }}" required></label>
          <label>Height <input type="number" name="height" step="1" min="1" value="{{ height or '' }}" required></label>
          <p class="muted">Dim factor: {{ 166 if quote_mode=='Air' else 139 }}</p>
          {% if calc_weight is not none %}
            <p class="callout">Calculated Dimensional Weight: <strong>{{ '%.2f'|format(calc_weight) }} lbs</strong></p>
          {% endif %}
        {% endif %}
      </div>

      <div class="stack">
        <h4>🔧 Accessorials</h4>
        {% for label in accessorial_labels %}
          <label>
            <input type="checkbox" name="accessorials" value="{{ label }}" {% if label in selected %}checked{% endif %} />
            {{ label }}
          </label>
        {% endfor %}
      </div>
    </div>

    <button type="submit" name="action" value="quote" class="btn-primary">Get Quote</button>
  </form>

  {% if result %}
    <hr/>
    <h3>Estimated Total: ${{ '%.2f'|format(result.total) }}</h3>
    <p>Weight: {{ '%.2f'|format(result.weight) }} | Weight Break: {{ result.weight_break }} | Per LB: {{ result.per_lb }} | Min Charge: {{ result.min_charge }}</p>
    {% if result.mode == 'Hotshot' %}
      <p>Zone: {{ result.zone }} | Exact Miles: {{ '%.2f'|format(result.miles) }}</p>
    {% else %}
      <p>Concat Zone: {{ result.concat }} | Beyond: ${{ '%.2f'|format(result.beyond_total) }} (Origin {{ result.origin_beyond or 'N/A' }}: ${{ '%.2f'|format(result.origin_charge) }}, Dest {{ result.dest_beyond or 'N/A' }}: ${{ '%.2f'|format(result.dest_charge) }})</p>
    {% endif %}
    <p>Accessorials: ${{ '%.2f'|format(result.accessorial_total) }}</p>

    {% if result.alert %}
      <article class="callout">🚨 <strong>Please contact FSI</strong> to confirm the most correct rate for your shipment.<br/>Phone: 800-651-0423 • Email: Operations@freightservices.net</article>
    {% endif %}

    <form method="post" action="{{ url_for('quote_bp.quote') }}">
      <input type="hidden" name="persist" value="1" />
      {% for k,v in result.persist_fields.items() %}
        <input type="hidden" name="{{ k }}" value="{{ v }}" />
      {% endfor %}
      <button type="submit" class="btn-primary">Save Quote</button>
      <a role="button" class="secondary" href="https://freightservices.ts2000.net/login?returnUrl=%2FLogin%2F" target="_blank">Book Shipment</a>
    </form>
  {% endif %}
{% endblock %}
"""

ADMIN_QUOTES = """
{% extends 'base.html' %}
{% block content %}
  <h2>📦 All Submitted Quotes</h2>
  <table>
    <thead>
      <tr>
        <th>Quote ID</th><th>User ID</th><th>User Email</th><th>Type</th><th>Origin</th><th>Destination</th><th>Weight</th><th>Method</th><th>Zone</th><th>Total</th><th>Accessorials</th><th>Date</th>
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
          <td>{{ q.weight }}</td>
          <td>{{ q.weight_method }}</td>
          <td>{{ q.zone }}</td>
          <td>${{ '%.2f'|format(q.total) }}</td>
          <td>{{ q.quote_metadata }}</td>
          <td>{{ q.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}
"""

from jinja2 import DictLoader

def _ensure_templates(app):
    # Allows drop-in usage without creating physical template files
    if not isinstance(app.jinja_loader, DictLoader):
        app.jinja_loader = DictLoader({})
    app.jinja_loader.mapping.setdefault('base.html', BASE)
    app.jinja_loader.mapping.setdefault('quote_form.html', QUOTE_FORM)
    app.jinja_loader.mapping.setdefault('admin_quotes.html', ADMIN_QUOTES)

# ---------- Routes ----------

@quote_bp.route("/quote", methods=["GET", "POST"])
def quote():
    # Provide defaults and redisplay form on POST as needed
    workbook = pd.read_excel(Config.WORKBOOK_PATH, sheet_name=None)

    accessorials_df = workbook["Accessorials"].copy()
    accessorials_df.columns = accessorials_df.columns.str.strip().str.upper()

    quote_mode = (request.form.get("quote_mode") or request.args.get("quote_mode") or "Hotshot").strip()
    weight_input_method = request.form.get("weight_input_method") or "Actual Weight"

    # Accessorial label map mirrors Streamlit logic
    if quote_mode == "Hotshot":
        options = {
            "4hr Window Pickup/Delivery": "4hr Window",
            "Specific Time Pickup/Delivery": "Less than 4 hrs",
            "Afterhours Pickup (Return Only)": "After Hours",
            "Weekend Pickup/Delivery": "Weekend",
            "Two-Man Team Pickup/Delivery": "Two Man",
            "Liftgate Pickup/Delivery": "Liftgate",
        }
    else:
        options = {
            "Guarantee Service (25%, Deliveries Only)": "Guarantee",
            "Anything less than 8hrs but more than 4hrs": "4hr Window",
            "4hrs or less Pickup/Delivery": "Less than 4 hrs",
            "After Hours": "After Hours",
            "Weekend Pickup/Delivery": "Weekend",
            "Two-Man Team Pickup/Delivery": "Two Man",
            "Liftgate Pickup/Delivery": "Liftgate",
        }

    selected = request.form.getlist("accessorials") if request.method == 'POST' else []

    origin = request.form.get("origin", "")
    destination = request.form.get("destination", "")

    length = request.form.get("length", type=float)
    width = request.form.get("width", type=float)
    height = request.form.get("height", type=float)

    weight = request.form.get("weight", type=float)
    calc_weight = None

    if weight_input_method == "Dimensional Weight" and all(v is not None for v in [length, width, height]):
        dim_factor = 166 if quote_mode == "Air" else 139
        calc_weight = (length * width * height) / dim_factor
        weight = calc_weight

    result = None

    # If saving a previously computed quote
    if request.method == 'POST' and request.form.get('persist') == '1':
        try:
            with Session() as db:
                zone = request.form.get('zone')
                concat = request.form.get('concat')
                quote_total = float(request.form.get('quote_total'))
                weight_break = float(request.form.get('weight_break')) if request.form.get('weight_break') else None
                per_lb = float(request.form.get('per_lb')) if request.form.get('per_lb') else None
                min_charge = float(request.form.get('min_charge')) if request.form.get('min_charge') else None
                meta = request.form.get('quote_metadata', '')

                q = Quote(
                    user_id=session.get('user'),
                    user_email=session.get('email', ''),
                    quote_type=quote_mode,
                    origin=origin,
                    destination=destination,
                    weight=weight or 0.0,
                    weight_method=("Dimensional" if weight_input_method == "Dimensional Weight" else "Actual"),
                    zone=(zone if quote_mode == 'Hotshot' else (concat or '')),
                    total=quote_total,
                    quote_metadata=meta,
                )
                db.add(q)
                db.commit()
                flash(f"Quote saved (ID: {q.quote_id})", "info")
                return redirect(url_for('quote_bp.quote'))
        except Exception as e:
            flash(f"Quote save failed: {e}", "warning")

    # Compute quote if requested
    if request.method == 'POST' and request.form.get('action') == 'quote':
        try:
            # Accessorial total
            accessorial_total = 0.0
            for label in selected:
                key = options[label].upper()
                if key != "GUARANTEE":
                    cost = float(accessorials_df[key].values[0])
                    accessorial_total += cost

            if quote_mode == "Hotshot":
                rates_df = workbook["Hotshot Rates"].copy()
                rates_df.columns = rates_df.columns.str.strip().str.upper()
                rates_df["MILES"] = pd.to_numeric(rates_df["MILES"], errors="coerce")

                miles = get_distance_miles(origin, destination) or 0.0

                zone = "X"
                for _, row in rates_df[["MILES", "ZONE"]].dropna().sort_values("MILES").iterrows():
                    if miles <= row["MILES"]:
                        zone = row["ZONE"]
                        break

                is_zone_x = str(zone).upper() == "X"
                per_lb = float(rates_df.loc[rates_df["ZONE"] == zone, "PER LB"].values[0])
                fuel_pct = float(rates_df.loc[rates_df["ZONE"] == zone, "FUEL"].values[0])
                min_charge = float(rates_df.loc[rates_df["ZONE"] == zone, "MIN"].values[0])
                weight_break = float(rates_df.loc[rates_df["ZONE"] == zone, "WEIGHT BREAK"].values[0])

                if is_zone_x:
                    rate_per_mile = float(rates_df.loc[rates_df["ZONE"] == zone, "MIN"].values[0])
                    miles_charge = miles * rate_per_mile * (1 + fuel_pct)
                    subtotal = miles_charge + accessorial_total
                else:
                    base = max(min_charge, (weight or 0) * per_lb)
                    subtotal = base * (1 + fuel_pct) + accessorial_total

                quote_total = subtotal
                alert = (quote_total > 6000) or ((weight or 0) > 5000)

                result = {
                    'total': quote_total,
                    'weight': weight or 0.0,
                    'weight_break': weight_break,
                    'per_lb': per_lb,
                    'min_charge': min_charge,
                    'accessorial_total': accessorial_total,
                    'mode': 'Hotshot',
                    'zone': zone,
                    'miles': miles,
                    'alert': alert,
                    'persist_fields': {
                        'zone': zone,
                        'quote_total': quote_total,
                        'weight_break': weight_break,
                        'per_lb': per_lb,
                        'min_charge': min_charge,
                        'quote_metadata': ", ".join(selected),
                        'origin': origin,
                        'destination': destination,
                        'weight': weight or 0.0,
                        'weight_input_method': weight_input_method,
                        'quote_mode': quote_mode,
                    }
                }

            else:  # Air
                zip_zone_df = workbook["ZIP CODE ZONES"].copy()
                cost_zone_table = workbook["COST ZONE TABLE"].copy()
                air_cost_df = workbook["Air Cost Zone"].copy()
                beyond_df = workbook["Beyond Price"].copy()

                for df in (zip_zone_df, cost_zone_table, air_cost_df, beyond_df):
                    df.columns = df.columns.str.strip().str.upper()

                orig_zone = int(zip_zone_df[zip_zone_df["ZIPCODE"] == int(origin)]["DEST ZONE"].values[0])
                dest_zone = int(zip_zone_df[zip_zone_df["ZIPCODE"] == int(destination)]["DEST ZONE"].values[0])
                concat = int(f"{orig_zone}{dest_zone}")

                cost_zone = cost_zone_table[cost_zone_table["CONCATENATE"] == concat]["COST ZONE"].values[0]
                cost_row = air_cost_df[air_cost_df["ZONE"].astype(str).str.strip() == str(cost_zone).strip()].iloc[0]

                min_charge = float(cost_row["MIN"])  # already numeric in your sheet
                per_lb = float(str(cost_row["PER LB"]).replace("$", "").replace(",", ""))
                weight_break = float(cost_row["WEIGHT BREAK"])  # assume numeric

                if (weight or 0) > weight_break:
                    base = (((weight or 0) - weight_break) * per_lb) + min_charge
                else:
                    base = min_charge

                quote_total = base + accessorial_total

                def get_beyond_zone(zipcode):
                    row = zip_zone_df[zip_zone_df["ZIPCODE"] == int(zipcode)]
                    if not row.empty and "BEYOND" in row.columns:
                        val = str(row["BEYOND"].values[0]).strip().upper()
                        if val in ("", "N/A", "NO", "NONE", "NAN"):
                            return None
                        return val.split()[-1]
                    return None

                def get_beyond_rate(zone_code):
                    if not zone_code:
                        return 0.0
                    match = beyond_df[beyond_df["ZONE"].astype(str).str.strip().str.upper() == zone_code]
                    if not match.empty:
                        try:
                            return float(str(match["RATE"].values[0]).replace("$", "").replace(",", "").strip())
                        except Exception:
                            return 0.0
                    return 0.0

                origin_beyond = get_beyond_zone(origin)
                dest_beyond = get_beyond_zone(destination)
                origin_charge = get_beyond_rate(origin_beyond)
                dest_charge = get_beyond_rate(dest_beyond)

                beyond_total = origin_charge + dest_charge
                quote_total += beyond_total

                if "Guarantee Service (25%, Deliveries Only)" in selected:
                    quote_total *= 1.25

                alert = (quote_total > 6000) or ((weight or 0) > 1200)

                result = {
                    'total': quote_total,
                    'weight': weight or 0.0,
                    'weight_break': weight_break,
                    'per_lb': per_lb,
                    'min_charge': min_charge,
                    'accessorial_total': accessorial_total,
                    'mode': 'Air',
                    'concat': concat,
                    'origin_beyond': origin_beyond,
                    'dest_beyond': dest_beyond,
                    'origin_charge': origin_charge,
                    'dest_charge': dest_charge,
                    'beyond_total': beyond_total,
                    'alert': alert,
                    'persist_fields': {
                        'concat': concat,
                        'quote_total': quote_total,
                        'weight_break': weight_break,
                        'per_lb': per_lb,
                        'min_charge': min_charge,
                        'quote_metadata': ", ".join(selected),
                        'origin': origin,
                        'destination': destination,
                        'weight': weight or 0.0,
                        'weight_input_method': weight_input_method,
                        'quote_mode': quote_mode,
                    }
                }

        except Exception as e:
            flash(f"Quote failed: {e}", "warning")

    # Render form with current state
    from flask import current_app
    _ensure_templates(current_app)

    accessorial_labels = list(options.keys())

    return render_template_string(
        QUOTE_FORM,
        title='Get Quote',
        quote_mode=quote_mode,
        weight_input_method=weight_input_method,
        origin=origin,
        destination=destination,
        length=length,
        width=width,
        height=height,
        calc_weight=calc_weight,
        selected=selected,
        accessorial_labels=accessorial_labels,
        result=result,
    )


@quote_bp.route("/admin/quotes")
def admin_quotes():
    # Simple guard; replace with your central @require_admin if available
    if session.get("role") != "admin":
        flash("Admin login required.", "warning")
        return redirect(url_for("quote_bp.quote"))

    with Session() as db:
        quotes = db.query(Quote).all()

    from flask import current_app
    _ensure_templates(current_app)

    return render_template_string(ADMIN_QUOTES, title='All Quotes', quotes=quotes)

# ---------- How to use ----------
# from quote_blueprint import quote_bp
# app.register_blueprint(quote_bp)
# Ensure static/FSI-logo.png exists
# Set GOOGLE_MAPS_API_KEY in environment for distance calc (optional)
