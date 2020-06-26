from functools import lru_cache
import pandas as pd


def max_date(df):
    return pd.Timestamp(df["date"].max().item(0)).date()


@lru_cache()
def read_excel(*args, **kwargs):
    return pd.read_excel(*args, **kwargs)


@lru_cache()
def read_csv(*args, **kwargs):
    return pd.read_csv(*args, **kwargs)
