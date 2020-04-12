import pandas as pd
import xarray as xr
from .util import max_date


def cases_covidtracking():
    url = "http://covidtracking.com/api/us/daily.csv"

    us_data = (
        pd.read_csv(url, parse_dates=[0], index_col=[0])
        .rename(
            columns={
                "positive": "cases",
                "death": "deaths",
                "totalTestResults": "tests",
            }
        )
        .sort_index()
    )

    data = xr.Dataset.from_dataframe(us_data[["cases", "deaths", "tests"]]).expand_dims(
        {"location": ["United States"]}
    )
    data.attrs["date"] = max_date(data)
    data.attrs["source"] = "COVID Tracking Project"
    data.attrs["source_url"] = url

    return data
