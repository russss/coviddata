import pandas as pd
import xarray as xr
from datetime import datetime


def imperial_interventions():
    url = "https://raw.githubusercontent.com/ImperialCollegeLondon/covid19model/master/data/interventions.csv"
    df = pd.read_csv(url, parse_dates=[3], dayfirst=True).rename(
        columns={
            "Date effective": "date",
            "Event": "event",
            "Type": "type",
            "Country": "location",
        }
    )
    df = df.drop(columns=df.columns.difference(["date", "event", "type", "location"]))
    df = df.set_index("location")

    data = xr.Dataset.from_dataframe(df).set_coords(["date"])
    data.attrs["date"] = datetime.now()
    data.attrs["source"] = "Imperial College London"
    data.attrs["source_url"] = url
    return data
