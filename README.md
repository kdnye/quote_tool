# 📦 Quote Tool

An internal Streamlit web app to generate logistics pricing quotes based on ZIP codes, shipment weight (actual or dimensional), and accessorial charges. Supports two quote types: **Hotshot** and **Air**.

---

## 🚀 Features

### 🔐 User Authentication

* Registration, Login, Password Reset
* Password complexity enforcement

### 🧑‍💼 Admin Dashboard

* Approve users
* Change user roles
* Delete users

### 📈 Dynamic Quote Engine

* Selectable quote mode: Hotshot or Air
* Actual weight or dimensional weight calculation
* Optional accessorials (based on mode)
* Mileage calculation via Google Maps API
* Rate logic driven by Excel (`HotShot Quote.xlsx`)
* Quote warnings for:

  * Total > \$6000
  * Weight > 1200 lbs (Air) or 5000 lbs (Hotshot)
* Launch "Book Shipment" link when quote is returned

### 📂 Quote Storage

* Quotes saved to `app.db` per user
* Includes all quote metadata

---

## 🛠 Setup Instructions

### 1. Environment

Python 3.8+

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Key packages: `streamlit`, `sqlalchemy`, `pandas`, `openpyxl`, `werkzeug`, `requests`

### 3. Required Files

Place the following in your project root:

* `HotShot Quote.xlsx` — contains rate tables and accessorials
* `.env` file with configuration values:

  ```
  # Required for mileage lookups
  GOOGLE_MAPS_API_KEY=your_api_key_here

  # Optional overrides
  DATABASE_URL=sqlite:///app.db
  SECRET_KEY=dev-secret-key
  WORKBOOK_PATH=HotShot Quote.xlsx
  ```

  These variables can also be supplied at runtime via your deployment platform's
  environment injection.

### 4. Launch the App

```bash
streamlit run app.py
```

---

## 🔧 Admin Access

A default admin account is seeded on first run:

* **Email:** `admin@example.com`
* **Password:** `SuperSecurePass!123`
  *(Change in `init_db.py` if needed)*

---

## 🗓 Database Schema

### `users` Table

* `id`, `name`, `email`, `phone`, `business_name`, `password_hash`, `role`, `is_approved`, `created_at`

### `quotes` Table

* `id`, `user_id`, `user_email`, `quote_type`, `origin`, `destination`, `weight`, `zone`, `total`, `quote_metadata`, `created_at`

---

## 📋 Accessorial Charges

* Pulled dynamically from Excel
* Separate options for Hotshot and Air
* Accessorial totals included in final quote

---

## 🔒 Password Requirements

* Minimum 14 characters with mix of upper/lower/number/symbol
  **OR**
* Passphrase ≥24 characters (letters only)

---

## 💡 Developer Notes

* Streamlit session state used for auth + page routing
* SQLAlchemy manages all ORM/database logic
* Rate logic isolated from DB to allow workbook-driven pricing
* Admin panel uses raw SQL for clarity and simplicity

---

## 📌 Roadmap / Next Steps

1. **Quote Traceability & Auditability**

   * Store complete quote details:

     * Origin/Destination
     * Accessorials
     * Quoted weight
     * Weight method (actual/dimensional)
     * Unique Quote ID

2. **Customer-Specific Rate Support**

   * Store and use different rate matrices per customer login

3. **Robust Quote History Backend**

   * Enable querying, filtering, and exporting of prior quotes

4. **Email Quote Request Button**

   * Adds `$15 administrative fee`
   * Launches a form for:

     * Shipper/Consignee details
  * Triggers local email client with:

     * Formatted `.csv` attachment compatible with TMS

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
