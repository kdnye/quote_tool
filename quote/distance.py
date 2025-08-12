# quote/distance.py
import os
import requests

def _get_secret(name: str):
    # Try Streamlit secrets first, but don't crash if secrets.toml is missing.
    try:
        import streamlit as st
        # st.secrets.get() still triggers a parse (and can raise) if no file exists,
        # so guard with try/except around the access as well.
        try:
            return st.secrets[name]
        except Exception:
            return None
    except Exception:
        return None

def get_distance_miles(origin_zip, destination_zip):
    api_key = _get_secret("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None
    url = (
        "https://maps.googleapis.com/maps/api/directions/json"
        f"?origin={origin_zip}&destination={destination_zip}&mode=driving&key={api_key}"
    )
    try:
        response = requests.get(url, timeout=20)
        data = response.json()
        if data.get("status") == "OK":
            meters = data["routes"][0]["legs"][0]["distance"]["value"]
            return meters / 1609.344
    except Exception:
        return None
