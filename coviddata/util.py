from functools import lru_cache
from http.client import HTTPException
from time import sleep
import traceback
import logging
import pandas as pd

log = logging.getLogger(__name__)


def max_date(df):
    return pd.Timestamp(df["date"].max().item(0)).date()


@lru_cache()
def read_excel(*args, **kwargs):
    return pd.read_excel(*args, **kwargs)


def read_csv(*args, **kwargs):
    log.info("Fetching CSV: %s", args[0])
    retries = 3
    while True:
        try:
            return pd.read_csv(*args, **kwargs)
        except (HTTPException, ConnectionError) as e:
            if retries == 0:
                raise
            retries -= 1
            log.warn("Error %s reading CSV, retrying %s more times", e, retries)
            sleep(2)


def deduplicate(df):
    """Messy hack to identify and remove duplicate values in a Pandas dataframe.

    The coronavirus.data.gov.uk API returns dupes sometimes and I don't know why.
    """
    dupes = df.index.duplicated()
    if any(dupes):
        print("Duplicates found!")
        print(df[dupes])
        print("Stack trace:")
        traceback.print_stack(limit=5)
    return df[~dupes]
