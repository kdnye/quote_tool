# File: utils.py
import pandas as pd

def normalize_workbook(workbook):
    for sheet in workbook.values():
        sheet.columns = sheet.columns.str.strip().str.upper()
    return workbook

def calculate_accessorials(selected_labels, accessorials_df, options):
    total = 0
    for label in selected_labels:
        key = options[label].upper()
        if key != "GUARANTEE":
            cost = float(accessorials_df[key].values[0])
            total += cost
    return total