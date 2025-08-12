# File: distance.py
import os
import requests

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

