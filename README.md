# quote_tool
Here's a draft `README.md` file for your GitHub project based on the code and database files you've provided:

---

# 📦 Quote Tool

A Streamlit-based internal web app for generating logistics pricing quotes based on origin/destination ZIP codes, shipment weight, and optional accessorials. The app supports two quoting modes: **Hotshot** and **Air**.

---

## 🚀 Features

* 🔐 User Authentication (Registration, Login, Password Reset)
* 📬 Admin Dashboard for user management (approve, delete, change roles)
* 📈 Dynamic Quote Calculation based on:

  * Mileage (Google Maps API)
  * Rate tables from `HotShot Quote.xlsx`
  * Optional accessorial charges
* 🧾 Quote History saved per user in a local SQLite database
* 🧪 Simple database setup and auto-table creation on startup

---

## 🛠 Setup Instructions

### 1. Environment

Python 3.8+

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

<sub>Example packages used: `streamlit`, `sqlalchemy`, `pandas`, `openpyxl`, `werkzeug`, `requests`</sub>

### 3. Required Files

Place the following in your project root:

* `HotShot Quote.xlsx` — contains rate tables for both quote types
* `.env` file with your Google Maps API key:

```
GOOGLE_MAPS_API_KEY=your_api_key_here
```

### 4. Launch the App

```bash
streamlit run app.py
```

---

## 🔧 Admin Access

Upon first run, a default admin account is seeded:

* **Email:** `admin@example.com`
* **Password:** `SuperSecurePass!123`

Change this in `init_db.py` if needed.

---

## 🗃 Database Schema

SQLite database (`app.db`) contains:

### `users`

* `id`, `name`, `email`, `phone`, `business_name`, `password_hash`, `role`, `is_approved`, `created_at`

### `quotes`

* `id`, `user_id`, `quote_type`, `origin`, `destination`, `weight`, `zone`, `total`, `quote_metadata`, `created_at`

---

## 📋 Accessorial Charges

Defined dynamically per mode (Hotshot or Air) from `Accessorials` sheet in the workbook. Added interactively during quoting.

---

## 🔒 Password Requirements

Password must:

* Be **≥14 characters** with a mix of uppercase, lowercase, number, symbol
* **OR** be a **24+ character passphrase** (letters only)

---

## 🧑‍💻 Developer Notes

* Streamlit session state drives user context and page navigation
* SQLAlchemy handles ORM and DB schema
* Admin actions (approve, change role, delete) use raw SQL commands for simplicity

---

## 📌 Roadmap / TODO

* ✅ Add Air quoting model
* ⏳ Implement export/download of quote history
* ⏳ Localization (e.g., Mexico VAT support)
* ⏳ Replace Google Maps API with OSRM for cost control

---

Let me know if you'd like this saved to a file or formatted for GitHub-flavored Markdown.
