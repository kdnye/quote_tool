import pandas as pd
import re

def normalize_workbook(workbook):
    for sheet_name, df in workbook.items():
        df.columns = df.columns.str.strip()
        workbook[sheet_name] = df
    return workbook

def _pick_name_column(df: pd.DataFrame) -> str:
    preferred = {"ACCESSORIAL", "ACCESSORIALS", "NAME", "DESCRIPTION", "LABEL", "SERVICE", "OPTION"}
    for c in df.columns:
        if str(c).strip().upper() in preferred:
            return c
    for c in df.columns:
        s = df[c].astype(str).str.strip()
        isnum = s.str.match(r"^\$?\s*\d+[,\d]*(\.\d+)?\s*%?$", na=False)
        if (1.0 - isnum.mean()) >= 0.5:
            return c
    return df.columns[0]

def _find_col(df: pd.DataFrame, *targets) -> str | None:
    targets = {t.upper() for t in targets}
    for c in df.columns:
        if str(c).strip().upper() in targets:
            return c
    for c in df.columns:
        cu = str(c).strip().upper()
        if any(t in cu for t in targets):
            return c
    return None

def _to_number(x) -> float:
    s = str(x).strip().replace("$", "").replace(",", "")
    if s.endswith("%"):
        s = s[:-1]
    try:
        return float(s)
    except Exception:
        return float("nan")

def calculate_accessorials(accessorials_df, selected, quote_mode, actual_weight):
    df = accessorials_df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    name_col   = _pick_name_column(df)
    type_col   = _find_col(df, "TYPE")
    rate_col   = _find_col(df, "RATE", "COST", "PRICE")
    weight_col = _find_col(df, "WEIGHT", "WT")

    total = 0.0
    names = df[name_col].astype(str).str.strip()

    for acc in selected:
        mask = names.eq(str(acc).strip())
        if not mask.any():
            continue
        rows = df.loc[mask].copy()

        # Determine rate type (fallback by inspecting the rate value)
        if type_col is not None:
            rate_type = str(rows.iloc[0][type_col]).strip().upper()
        else:
            rate_type = ""

        if not rate_type:
            raw = str(rows.iloc[0][rate_col]) if rate_col is not None else ""
            rate_type = "PERCENTAGE" if raw.strip().endswith("%") else "FIXED"

        if rate_type in ("FIXED", "FLAT"):
            if rate_col is not None:
                val = _to_number(rows.iloc[0][rate_col])
                if pd.notna(val):
                    total += val

        elif rate_type == "PERCENTAGE":
            if rate_col is not None:
                val = _to_number(rows.iloc[0][rate_col])
                if val > 1.0:
                    val /= 100.0
                if pd.notna(val):
                    total += val * float(actual_weight or 0.0)

        elif rate_type == "WEIGHT BREAK":
            if rate_col is None:
                continue
            if weight_col is None:
                val = _to_number(rows.iloc[0][rate_col])
                if pd.notna(val):
                    total += val
            else:
                tmp = rows.copy()
                tmp[weight_col] = pd.to_numeric(tmp[weight_col], errors="coerce")
                tmp = tmp.dropna(subset=[weight_col]).sort_values(weight_col)
                if tmp.empty:
                    continue
                w = float(actual_weight or 0.0)
                match = tmp[tmp[weight_col] >= w].head(1)
                if match.empty:
                    match = tmp.tail(1)
                val = _to_number(match.iloc[0][rate_col])
                if pd.notna(val):
                    total += val

    return total
