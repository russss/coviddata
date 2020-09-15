from functools import lru_cache
import traceback
import pandas as pd


def max_date(df):
    return pd.Timestamp(df["date"].max().item(0)).date()


@lru_cache()
def read_excel(*args, **kwargs):
    return pd.read_excel(*args, **kwargs)


@lru_cache()
def read_csv(*args, **kwargs):
    return pd.read_csv(*args, **kwargs)


def deduplicate(df):
    """ Messy hack to identify and remove duplicate values in a Pandas dataframe.
            
        The coronavirus.data.gov.uk API returns dupes sometimes and I don't know why.
    """
    dupes = df.index.duplicated()
    if any(dupes):
        print("Duplicates found!")
        print(df[dupes])
        print("Stack trace:")
        traceback.print_stack(limit=5)
    return df[~dupes]
