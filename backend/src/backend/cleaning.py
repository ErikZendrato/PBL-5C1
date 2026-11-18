import pandas as pd


def clean_numeric(value, default=0.0):
    if pd.isna(value) or str(value).strip() == "":
        return default
    return pd.to_numeric(str(value).replace(",", "."), errors="coerce")

