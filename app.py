from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from functools import wraps
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from db import Session, User, Base, engine

# [Unverified] If you have a real Config class, keep this import; otherwise, define a minimal one.
try:
    from config import Config  # expects SECRET_KEY, etc.
except Exception:
    class Config:
        SECRET_KEY = "dev-change-me"

app = Flask(__name__, static_url_path="/static", static_folder="static")
app.config.from_object(Config)
Base.metadata.create_all(engine)

# ---- Session defaults ----
@app.before_request
def set_defaults():
    # Honor query params (?page=...)
    page = request.args.get("page")
    if page:
        # redirect to the canonical route for that page
        return redirect(url_for(page)) if page in {"auth","quote","email_request","admin"} else None

    # Initialize session keys
    session.setdefault("page", "quote")      # PUBLIC by default
    session.setdefault("role", "guest")      # guest/user/admin

# Ensure DB sessions are cleaned up
@app.teardown_request
def remove_session(exception=None):
    Session.remove()

# ---- Auth helpers ----
def require_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin login required.", "warning")
            return redirect(url_for("auth"))
        return view(*args, **kwargs)
    return wrapped

# ---- Data store ----
QUOTES = []  # simple list for demo purposes

# Ensure a default admin user exists in the database
_init_sess = Session()
if not _init_sess.query(User).filter_by(email="admin@example.com").first():
    admin = User(
        name="FSI Admin",
        email="admin@example.com",
        password_hash=generate_password_hash("admin123"),
        role="admin",
    )
    _init_sess.add(admin)
    _init_sess.commit()
Session.remove()

# ---- Templates (inline for single-file demo) ----
BASE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{{ title or 'Quote Tool' }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css" />
    <style>
      header.nav { display:flex; align-items:center; gap:1rem; margin-bottom:1rem; }
      header.nav img { height: 48px; }
      .right { margin-left:auto; display:flex; gap:.5rem; align-items:center; }
      .container { max-width: 1100px; }
      .badge { padding:.15rem .5rem; border-radius:.5rem; background:#eef; }
    </style>
  </head>
  <body>
    <nav class="container">
      <header class="nav">
        <a href="{{ url_for('quote') }}" class="contrast" style="display:flex;align-items:center;gap:.5rem;">
          <img src="{{ url_for('static', filename='FSI-logo.png') }}" alt="FSI" />
          <strong>Quote Tool</strong>
        </a>
        <div class="right">
          <a role="button" href="{{ url_for('quote') }}">Get Quote</a>
          {% if session.get('role') == 'admin' %}
            <span class="badge">Admin: {{ session.get('name','') }}</span>
            <a role="button" href="{{ url_for('admin') }}">Admin Dashboard</a>
            <a role="button" class="secondary" href="{{ url_for('logout') }}">Log out</a>
          {% else %}
            <a role="button" class="secondary" href="{{ url_for('auth') }}">Admin Login</a>
          {% endif %}
        </div>
      </header>
    </nav>

    <main class="container">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          <div>
            {% for cat, msg in messages %}
              <article class="{{ 'secondary' if cat=='info' else '' }}">{{ msg }}</article>
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}

      {% block content %}{% endblock %}
    </main>
  </body>
</html>
"""

AUTH = """
{% extends 'base.html' %}
{% block content %}
  <h2>Authentication</h2>
  <details open>
    <summary>Login</summary>
    <form method="post" action="{{ url_for('login') }}">
      <label>Email <input type="email" name="email" required /></label>
      <label>Password <input type="password" name="password" required /></label>
      <button type="submit">Login</button>
    </form>
  </details>

  <details>
    <summary>Register</summary>
    <form method="post" action="{{ url_for('register') }}">
      <label>Email <input type="email" name="email" required /></label>
      <label>Password <input type="password" name="password" required /></label>
      <label>Name <input name="name" /></label>
      <button type="submit">Register</button>
    </form>
  </details>
{% endblock %}
"""

QUOTE = """
{% extends 'base.html' %}
{% block content %}
  <h2>Request a Quote</h2>
  <form method="post" action="{{ url_for('quote') }}">
    <div class="grid">
      <label>Origin <input name="origin" required /></label>
      <label>Destination <input name="destination" required /></label>
      <label>Weight (lbs) <input type="number" name="weight" min="1" step="any" required /></label>
      <label>Dims (LxWxH in) <input name="dims" placeholder="48x40x60" /></label>
    </div>
    <label>Service Level
      <select name="service">
        <option>Air</option>
        <option>Ocean</option>
        <option>Truckload</option>
        <option>LTL</option>
      </select>
    </label>
    <button type="submit">Get Quote</button>
  </form>

  {% if quote %}
    <article>
      <h3>Estimated Quote</h3>
      <p><strong>Price:</strong> ${{ '%.2f'|format(quote.price) }}</p>
      <p><strong>ETA:</strong> {{ quote.eta }}</p>
      <form method="post" action="{{ url_for('email_request') }}">
        <input type="hidden" name="quote_id" value="{{ quote.id }}" />
        <label>Email <input type="email" name="email" required value="{{ session.get('email','') }}" /></label>
        <button type="submit">Email me this quote</button>
      </form>
    </article>
  {% endif %}
{% endblock %}
"""

EMAIL = """
{% extends 'base.html' %}
{% block content %}
  <h2>Email Request</h2>
  {% if sent %}
    <article>Quote emailed to <strong>{{ email }}</strong> at {{ ts }}.</article>
  {% else %}
    <article>Nothing to email.</article>
  {% endif %}
{% endblock %}
"""

ADMIN = """
{% extends 'base.html' %}
{% block content %}
  <h2>🛠️ Admin Dashboard</h2>
  <form method="get" action="{{ url_for('admin') }}" style="margin-bottom:1rem;">
    <fieldset role="group">
      <input type="hidden" name="view" value="{{ view }}" />
      <a role="button" href="{{ url_for('admin', view='Manage Users') }}">Manage Users</a>
      <a role="button" href="{{ url_for('admin', view='View Quotes') }}">View Quotes</a>
    </fieldset>
  </form>

  {% if view == 'Manage Users' %}
    <h3>Users</h3>
    <table>
      <thead><tr><th>Email</th><th>Name</th><th>Role</th></tr></thead>
      <tbody>
        {% for u in users %}
          <tr><td>{{ u.email }}</td><td>{{ u.name }}</td><td>{{ u.role }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  {% elif view == 'View Quotes' %}
    <h3>Quotes</h3>
    <table>
      <thead><tr><th>ID</th><th>Origin</th><th>Destination</th><th>Weight</th><th>Service</th><th>Price</th><th>ETA</th><th>Requested</th></tr></thead>
      <tbody>
        {% for q in quotes %}
          <tr>
            <td>{{ q.id }}</td><td>{{ q.origin }}</td><td>{{ q.destination }}</td><td>{{ q.weight }}</td>
            <td>{{ q.service }}</td><td>${{ '%.2f'|format(q.price) }}</td><td>{{ q.eta }}</td><td>{{ q.ts }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% endif %}
{% endblock %}
"""

# Register templates with Flask's loader at runtime
from jinja2 import DictLoader
app.jinja_loader = DictLoader({
    'base.html': BASE,
    'auth.html': AUTH,
    'quote.html': QUOTE,
    'email.html': EMAIL,
    'admin.html': ADMIN,
})

# ---- Routes ----
@app.route('/')
def root():
    return redirect(url_for('quote'))

@app.route('/auth', methods=['GET'])
def auth():
    session['page'] = 'auth'
    return render_template_string(AUTH, title='Auth')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email','').strip().lower()
    password = request.form.get('password','')
    user = Session.query(User).filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        flash('Invalid credentials', 'warning')
        return redirect(url_for('auth'))
    session.update({
        'user': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role or 'user',
    })
    flash('Logged in successfully', 'info')
    return redirect(url_for('admin' if session.get('role')=='admin' else 'quote'))

@app.route('/register', methods=['POST'])
def register():
    email = request.form.get('email','').strip().lower()
    password = request.form.get('password','')
    name = request.form.get('name','').strip() or email
    if Session.query(User).filter_by(email=email).first():
        flash('Email already registered', 'warning')
        return redirect(url_for('auth'))
    user = User(name=name, email=email, password_hash=generate_password_hash(password), role='user')
    Session.add(user)
    Session.commit()
    flash('Registered. You can now log in.', 'info')
    return redirect(url_for('auth'))

@app.route('/logout')
def logout():
    for k in ('user','name','email','role'):
        session.pop(k, None)
    session['page'] = 'quote'
    flash('Logged out', 'info')
    return redirect(url_for('quote'))

@app.route('/quote', methods=['GET','POST'])
def quote():
    session['page'] = 'quote'
    quote_obj = None
    if request.method == 'POST':
        origin = request.form['origin']
        destination = request.form['destination']
        weight = float(request.form['weight'])
        dims = request.form.get('dims','')
        service = request.form.get('service','LTL')
        # [Unverified] Replace with your real quote calculation (or call existing module)
        price = 0.55 * weight + (15 if service.lower()=="air" else 5)
        eta = "2-4 days" if service.lower() in ("air","ltl") else "5-12 days"
        quote_obj = type('Quote', (), {})()
        quote_obj.id = len(QUOTES) + 1
        quote_obj.origin = origin
        quote_obj.destination = destination
        quote_obj.weight = weight
        quote_obj.dims = dims
        quote_obj.service = service
        quote_obj.price = price
        quote_obj.eta = eta
        quote_obj.ts = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        QUOTES.append(quote_obj)
        flash('Quote calculated', 'info')
    return render_template_string(QUOTE, quote=quote_obj, title='Get Quote')

@app.route('/email_request', methods=['POST','GET'])
def email_request():
    # In the original Streamlit app this was a separate UI step. Here we simulate an email-sent view.
    if request.method == 'POST':
        qid = int(request.form.get('quote_id','0'))
        email = request.form.get('email') or session.get('email')
        quote = next((q for q in QUOTES if q.id == qid), None)
        if not quote:
            flash('Quote not found', 'warning')
            return redirect(url_for('quote'))
        # [Unverified] Replace with real email send (e.g., SMTP/SES) and your email_form_ui logic
        sent = True
        ts = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        flash(f'Quote #{qid} emailed to {email}', 'info')
        return render_template_string(EMAIL, sent=sent, email=email, ts=ts, title='Email Sent')
    # GET fallback
    return render_template_string(EMAIL, sent=False, email='', ts='', title='Email')

@app.route('/admin')
@require_admin
def admin():
    session['page'] = 'admin'
    view = request.args.get('view', 'Manage Users')
    users = Session.query(User).all()
    return render_template_string(ADMIN, users=users, quotes=QUOTES, view=view, title='Admin')

if __name__ == '__main__':
    # Run: python app.py
    app.run(debug=True)
