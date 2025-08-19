# File: logic_air.py
import pandas as pd

def calculate_air_quote(origin, destination, weight, accessorial_total, workbook):
    zip_zone_df = workbook["ZIP CODE ZONES"]
    cost_zone_table = workbook["COST ZONE TABLE"]
    air_cost_df = workbook["Air Cost Zone"]
    beyond_df = workbook["Beyond Price"]

    # Dynamically find column names to prevent KeyErrors
    col_map = {
        'ZIPCODE': next((col for col in zip_zone_df.columns if 'ZIPCODE' in col.upper()), None),
        'DEST ZONE': next((col for col in zip_zone_df.columns if 'DEST ZONE' in col.upper()), None),
        'BEYOND': next((col for col in zip_zone_df.columns if 'BEYOND' in col.upper()), None),
        'CONCATENATE': next((col for col in cost_zone_table.columns if 'CONCATENATE' in col.upper()), None),
        'COST ZONE': next((col for col in cost_zone_table.columns if 'COST ZONE' in col.upper()), None),
        'AIR COST ZONE': next((col for col in air_cost_df.columns if 'ZONE' in col.upper()), None),
        'MIN': next((col for col in air_cost_df.columns if 'MIN' in col.upper()), None),
        'PER LB': next((col for col in air_cost_df.columns if 'PER LB' in col.upper()), None),
        'WEIGHT BREAK': next((col for col in air_cost_df.columns if 'WEIGHT BREAK' in col.upper()), None),
        'BEYOND ZONE': next((col for col in beyond_df.columns if 'ZONE' in col.upper()), None),
        'BEYOND RATE': next((col for col in beyond_df.columns if 'RATE' in col.upper()), None),
    }

    for key, col in col_map.items():
        if col is None:
            raise KeyError(f"Could not find a column containing '{key}' in the workbook. Please check your sheet headers.")

    # Convert the ZIPCODE column to a string for a proper comparison
    zip_zone_df[col_map['ZIPCODE']] = zip_zone_df[col_map['ZIPCODE']].astype(str).str.strip()

    def _error_result(msg):
        return {
            "zone": None,
            "quote_total": 0,
            "min_charge": None,
            "per_lb": None,
            "weight_break": None,
            "origin_beyond": None,
            "dest_beyond": None,
            "origin_charge": 0,
            "dest_charge": 0,
            "beyond_total": 0,
            "error": msg,
        }

    origin_row = zip_zone_df[zip_zone_df[col_map['ZIPCODE']] == str(origin)]
    if origin_row.empty:
        return _error_result(f"Origin ZIP code {origin} not found")

    dest_row = zip_zone_df[zip_zone_df[col_map['ZIPCODE']] == str(destination)]
    if dest_row.empty:
        return _error_result(f"Destination ZIP code {destination} not found")

    orig_zone = int(origin_row[col_map['DEST ZONE']].values[0])
    dest_zone = int(dest_row[col_map['DEST ZONE']].values[0])
    concat = int(f"{orig_zone}{dest_zone}")
    
    # Corrected: Use the dynamically found column name for 'CONCATENATE'
    cost_zone_table[col_map['CONCATENATE']] = pd.to_numeric(cost_zone_table[col_map['CONCATENATE']], errors='coerce').astype(str)
    
    # Corrected: Use the dynamically found column name for 'COST ZONE'
    cost_zone_match = cost_zone_table[cost_zone_table[col_map['CONCATENATE']] == str(concat)][col_map['COST ZONE']]
    if cost_zone_match.empty:
        return _error_result(f"Cost zone not found for concatenated zone {concat}")
    cost_zone = cost_zone_match.values[0]
    
    # Corrected: Use the dynamically found column name for the ZONE column in the 'Air Cost Zone' sheet
    air_cost_df[col_map['AIR COST ZONE']] = air_cost_df[col_map['AIR COST ZONE']].astype(str)
    
    cost_row_match = air_cost_df[air_cost_df[col_map['AIR COST ZONE']].str.strip() == str(cost_zone).strip()]
    if cost_row_match.empty:
        return _error_result(f"Air cost zone {cost_zone} not found")
    cost_row = cost_row_match.iloc[0]

    min_charge = float(cost_row[col_map['MIN']])
    per_lb = float(str(cost_row[col_map['PER LB']]).replace("$", "").replace(",", ""))
    weight_break = float(cost_row[col_map['WEIGHT BREAK']])
    
    if weight > weight_break:
        base = ((weight - weight_break) * per_lb) + min_charge
    else:
        base = min_charge

    def get_beyond_zone(zipcode):
        row = zip_zone_df[zip_zone_df[col_map['ZIPCODE']] == str(zipcode)]
        if not row.empty and col_map['BEYOND'] in row.columns:
            val = str(row[col_map['BEYOND']].values[0]).strip().upper()
            if val in ("", "N/A", "NO", "NONE", "NAN"):
                return None
            return val.split()[-1]
        return None

    def get_beyond_rate(zone_code):
        if not zone_code:
            return 0.0
        
        # Corrected: Use dynamic column names for beyond_df
        beyond_df[col_map['BEYOND ZONE']] = beyond_df[col_map['BEYOND ZONE']].astype(str)
        
        match = beyond_df[beyond_df[col_map['BEYOND ZONE']].str.strip().str.upper() == zone_code]
        if not match.empty:
            try:
                return float(str(match[col_map['BEYOND RATE']].values[0]).replace("$", "").replace(",", "").strip())
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
        "beyond_total": beyond_total,
        "error": None,
    }
