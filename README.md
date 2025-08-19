# 📦 Quote Tool

An internal **Flask** web application for generating logistics pricing
quotes based on ZIP codes, shipment weight (actual or dimensional), and
accessorial charges. The tool supports two quote types: **Hotshot** and
**Air**.

---

## 🚀 Features

- **User Authentication** – registration, login and password reset
- **Admin Dashboard** – approve users, change roles, delete users
- **Dynamic Quote Engine** – choose Hotshot or Air, calculate actual or
  dimensional weight, optional accessorials, Google Maps mileage lookup
  and Excel‑driven rate logic with quote warnings
- **Quote Storage** – quotes saved to `app.db` with full metadata

---

## 🛠 Setup Instructions

### 1. Environment

Python 3.8+

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Key packages: `Flask`, `SQLAlchemy`, `pandas`, `openpyxl`, `werkzeug`,
`requests`, `gunicorn`

### 3. Required Files

Place the following in your project root:

- `HotShot Quote.xlsx` — rate tables and accessorials
- `.env` file with configuration values:

  ```
  GOOGLE_MAPS_API_KEY=your_api_key_here

  # Database configuration
  # DATABASE_URL=mysql+pymysql://user:password@host:3306/quote_tool
  # or individual MYSQL_* settings

  SECRET_KEY=dev-secret-key
  WORKBOOK_PATH=HotShot Quote.xlsx
  ```

### 4. Launch the App

For development:

```bash
python flask_app.py
```

For production:

```bash
gunicorn flask_app:app
```

---

## 🔧 Admin Access

A default admin account is seeded on first run:

- **Email:** `admin@example.com`
- **Password:** `SuperSecurePass!123`
  *(Change in `init_db.py` if needed)*

---

## 🧮 Database Migrations

Alembic manages schema changes.

### Apply Latest Migration

```bash
alembic upgrade head
```

### Revert Last Migration

```bash
alembic downgrade -1
```

See `alembic.ini` for database connection configuration.

