
import streamlit as st
import pandas as pd
import os
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from db import Session, Quote
from io import BytesIO
import folium
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium

def get_distance_miles(origin_zip, destination_zip):
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin_zip}&destination={destination_zip}&mode=driving&key={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        if data["status"] == "OK":
            meters = data["routes"][0]["legs"][0]["distance"]["value"]
            return meters / 1609.344
    except:
        return None

def send_quote_email(to_email, subject, body):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

def show_map(origin_zip, destination_zip):
    geolocator = Nominatim(user_agent="quote_tool")
    origin_loc = geolocator.geocode(origin_zip)
    dest_loc = geolocator.geocode(destination_zip)

    if not origin_loc or not dest_loc:
        st.warning("Could not locate one or both zip codes.")
        return

    mid_lat = (origin_loc.latitude + dest_loc.latitude) / 2
    mid_lon = (origin_loc.longitude + dest_loc.longitude) / 2

    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=6)

    folium.Marker([origin_loc.latitude, origin_loc.longitude],
                  popup=f"Origin: {origin_zip}", icon=folium.Icon(color='green')).add_to(m)

    folium.Marker([dest_loc.latitude, dest_loc.longitude],
                  popup=f"Destination: {destination_zip}", icon=folium.Icon(color='red')).add_to(m)

    folium.PolyLine([(origin_loc.latitude, origin_loc.longitude),
                     (dest_loc.latitude, dest_loc.longitude)],
                    color="blue", weight=3, opacity=0.8).add_to(m)

    st_folium(m, width=700, height=500)
