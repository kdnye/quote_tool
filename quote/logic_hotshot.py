# File: logic_hotshot.py
try:
    from quote.distance import get_distance_miles
except ImportError:
    from distance import get_distance_miles
import pandas as pd

def calculate_hotshot_quote(origin, destination, weight, accessorial_total, rates_df):
    miles = get_distance_miles(origin, destination) or 0
    zone = "X"
    
    # Dynamically find column names to prevent KeyErrors
    col_map = {
        'MILES': next((col for col in rates_df.columns if 'MILES' in col.upper()), None),
        'ZONE': next((col for col in rates_df.columns if 'ZONE' in col.upper()), None),
        'PER LB': next((col for col in rates_df.columns if 'PER LB' in col.upper()), None),
        'FUEL': next((col for col in rates_df.columns if 'FUEL' in col.upper()), None),
        'MIN': next((col for col in rates_df.columns if 'MIN' in col.upper()), None),
        'WEIGHT BREAK': next((col for col in rates_df.columns if 'WEIGHT BREAK' in col.upper()), None)
    }

    for key, col in col_map.items():
        if col is None:
            raise KeyError(f"Could not find a column containing '{key}' in the Hotshot Rates sheet.")

    # Convert the miles column to a numeric type
    rates_df[col_map['MILES']] = pd.to_numeric(rates_df[col_map['MILES']], errors='coerce')

    for _, row in rates_df[[col_map['MILES'], col_map['ZONE']]].dropna().sort_values(col_map['MILES']).iterrows():
        if miles <= float(row[col_map['MILES']]):
            zone = row[col_map['ZONE']]
            break

    zone_col = rates_df[col_map['ZONE']].astype(str).str.upper()
    if str(zone).upper() not in zone_col.values:
        raise ValueError(f"Zone '{zone}' not found in the Hotshot Rates sheet.")

    is_zone_x = zone.upper() == "X"
    
    # Use the mapped column names to access data
    per_lb = float(rates_df.loc[rates_df[col_map['ZONE']].astype(str) == zone, col_map['PER LB']].values[0])
    fuel_pct = float(rates_df.loc[rates_df[col_map['ZONE']].astype(str) == zone, col_map['FUEL']].values[0])
    min_charge = float(rates_df.loc[rates_df[col_map['ZONE']].astype(str) == zone, col_map['MIN']].values[0])
    weight_break = float(rates_df.loc[rates_df[col_map['ZONE']].astype(str) == zone, col_map['WEIGHT BREAK']].values[0])

    if is_zone_x:
        rate_per_mile = float(rates_df.loc[rates_df[col_map['ZONE']].astype(str) == zone, col_map['MIN']].values[0])
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