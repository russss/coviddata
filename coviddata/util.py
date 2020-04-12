import pandas as pd


def max_date(df):
    return pd.Timestamp(df["date"].max().item(0)).date()
