# File: logic_air.py
import pandas as pd

def calculate_air_quote(origin, destination, weight, accessorial_total, workbook):
    zip_zone_df = workbook["ZIP CODE ZONES"]
    cost_zone_table = workbook["COST ZONE TABLE"]
    air_cost_df = workbook["Air Cost Zone"]
    beyond_df = workbook["Beyond Price"]

    orig_zone = int(zip_zone_df[zip_zone_df["ZIPCODE"] == int(origin)]["DEST ZONE"].values[0])
    dest_zone = int(zip_zone_df[zip_zone_df["ZIPCODE"] == int(destination)]["DEST ZONE"].values[0])
    concat = int(f"{orig_zone}{dest_zone}")
    cost_zone = cost_zone_table[cost_zone_table["CONCATENATE"] == concat]["COST ZONE"].values[0]
    cost_row = air_cost_df[air_cost_df["ZONE"].str.strip() == str(cost_zone).strip()].iloc[0]

    min_charge = float(cost_row["MIN"])
    per_lb = float(str(cost_row["PER LB"]).replace("$", "").replace(",", ""))
    weight_break = float(cost_row["WEIGHT BREAK"])
    
    if weight > weight_break:
        base = ((weight - weight_break) * per_lb) + min_charge
    else:
        base = min_charge

    def get_beyond_zone(zipcode):
        row = zip_zone_df[zip_zone_df["ZIPCODE"] == int(zipcode)]
        if not row.empty and "BEYOND" in row.columns:
            val = str(row["BEYOND"].values[0]).strip().upper()
            if val in ("", "N/A", "NO", "NONE", "NAN"):
                return None
            return val.split()[-1]
        return None

    def get_beyond_rate(zone_code):
        if not zone_code:
            return 0.0
        match = beyond_df[beyond_df["ZONE"].str.strip().str.upper() == zone_code]
        if not match.empty:
            try:
                return float(str(match["RATE"].values[0]).replace("$", "").replace(",", "").strip())
            except Exception:
                return 0.0
        return 0.0

    origin_beyond = get_beyond_zone(origin)
    dest_beyond = get_beyond_zone(destination)
    origin_charge = get_beyond_rate(origin_beyond)
    dest_charge = get_beyond_rate(dest_beyond)
    beyond_total = origin_charge + dest_charge

    quote_total = base + accessorial_total + beyond_total

    return {
        "zone": concat,
        "quote_total": quote_total,
        "min_charge": min_charge,
        "per_lb": per_lb,
        "weight_break": weight_break,
        "origin_beyond": origin_beyond,
        "dest_beyond": dest_beyond,
        "origin_charge": origin_charge,
        "dest_charge": dest_charge,
        "beyond_total": beyond_total
    }