import os
"index.html",
origin_zip=origin_zip,
destination_zip=dest_zip,
email=email,
miles=miles,
)


# GET
return render_template("index.html")




@app.route("/map", methods=["POST"]) # invoked from the index form
def map_view():
origin_zip = (request.form.get("origin_zip") or "").strip()
dest_zip = (request.form.get("destination_zip") or "").strip()


html = build_map_html(origin_zip, dest_zip)
if html is None:
flash("Could not locate one or both ZIP codes.", "warning")
return redirect(url_for("index"))


# Wrap in Markup so Jinja doesn't escape it
return render_template("map.html", map_html=Markup(html))




@app.route("/send", methods=["POST"]) # send quote email
def send_email_route():
origin_zip = (request.form.get("origin_zip") or "").strip()
dest_zip = (request.form.get("destination_zip") or "").strip()
email = (request.form.get("email") or "").strip()


if not email:
flash("Recipient email is required to send a quote.", "warning")
return redirect(url_for("index"))


miles = get_distance_miles(origin_zip, dest_zip)
miles_text = f"{miles:,.2f} miles" if miles is not None else "N/A"


subject = f"Quote for {origin_zip} → {dest_zip}"
body = (
f"Quote Details\n\n"
f"Origin ZIP: {origin_zip}\n"
f"Destination ZIP: {dest_zip}\n"
f"Estimated Distance: {miles_text}\n"
f"Generated: {datetime.utcnow().isoformat()}Z\n"
)


try:
send_quote_email(email, subject, body)
flash("Quote email sent.", "success")
except Exception as e:
app.logger.exception("Email send failed: %s", e)
flash("Failed to send email. Check SMTP settings.", "danger")


return redirect(url_for("index"))




if __name__ == "__main__":
# For local dev only; use a WSGI/ASGI server in production
app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
