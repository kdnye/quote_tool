# quote/distance.py
import os, requests

def _get_secret(name: str):
    try:
        import streamlit as st
        try:
            return st.secrets[name]
        except Exception:
            return None
    except Exception:
        return None

def _sanitize_zip(z: str) -> str | None:
    if not z:
        return None
    s = "".join(ch for ch in str(z).strip() if ch.isdigit())
    if len(s) == 5:
        return s + ",USA"     # helps disambiguate
    return None

def get_distance_miles(origin_zip, destination_zip):
    api_key = _get_secret("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        # Optional: print for Streamlit logs
        print("[distance] No GOOGLE_MAPS_API_KEY found")
        return None

    o = _sanitize_zip(origin_zip)
    d = _sanitize_zip(destination_zip)
    if not o or not d:
        print(f"[distance] Bad zips -> origin={origin_zip!r}, dest={destination_zip!r}")
        return None

    url = (
        "https://maps.googleapis.com/maps/api/directions/json"
        f"?origin={o}&destination={d}&mode=driving&key={api_key}"
    )
    try:
        r = requests.get(url, timeout=20)
        data = r.json()
        if data.get("status") == "OK":
            meters = data["routes"][0]["legs"][0]["distance"]["value"]
            miles = meters / 1609.344
            return miles
        else:
            # Surface the reason to Streamlit logs
            print(f"[distance] status={data.get('status')} error={data.get('error_message')}")
            return None
    except Exception as e:
        print(f"[distance] exception={e}")
        return None
