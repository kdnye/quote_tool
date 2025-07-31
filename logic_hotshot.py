# File: logic_hotshot.py
from quote.distance import get_distance_miles
import pandas as pd

def calculate_hotshot_quote(origin, destination, weight, accessorial_total, rates_df):
    miles = get_distance_miles(origin, destination) or 0
    zone = "X"
    for _, row in rates_df[["MILES", "ZONE"]].dropna().sort_values("MILES").iterrows():
        if miles <= row["MILES"]:
            zone = row["ZONE"]
            break

    is_zone_x = zone.upper() == "X"
    per_lb = float(rates_df.loc[rates_df["ZONE"] == zone, "PER LB"].values[0])
    fuel_pct = float(rates_df.loc[rates_df["ZONE"] == zone, "FUEL"].values[0])
    min_charge = float(rates_df.loc[rates_df["ZONE"] == zone, "MIN"].values[0])
    weight_break = float(rates_df.loc[rates_df["ZONE"] == zone, "WEIGHT BREAK"].values[0])

    if is_zone_x:
        rate_per_mile = float(rates_df.loc[rates_df["ZONE"] == zone, "MIN"].values[0])
        miles_charge = miles * rate_per_mile * (1 + fuel_pct)
        subtotal = miles_charge + accessorial_total
    else:
        base = max(min_charge, weight * per_lb)
        subtotal = base * (1 + fuel_pct) + accessorial_total

    return {
        "zone": zone,
        "miles": miles,
        "quote_total": subtotal,
        "weight_break": weight_break,
        "per_lb": per_lb,
        "min_charge": min_charge
    }