import pandas as pd
import xarray as xr
from .util import max_date


def cases_ecdc():
    url = "https://opendata.ecdc.europa.eu/covid19/casedistribution/csv"
    data = (
        pd.read_csv(url, parse_dates=[0], dayfirst=True)
        .drop(["day", "month", "year", "popData2018", "geoId"], axis=1)
        .rename(
            {
                "countriesAndTerritories": "location",
                "dateRep": "date",
                "countryterritoryCode": "iso3",
            },
            axis=1,
        )
    )

    data["location"] = data["location"].apply(lambda name: name.replace("_", " "))
    data = data.set_index(["location", "date"]).sort_index()
    data = xr.Dataset.from_dataframe(data).set_coords(["iso3"])

    # Make numbers cumulative to match other datasets
    data["deaths"] = data["deaths"].cumsum(dim="date")
    data["cases"] = data["cases"].cumsum(dim="date")

    return data


def cases_owid():
    url = "https://cowid.netlify.com/data/ecdc/full_data.csv"
    data = pd.read_csv(url, parse_dates=[0], index_col=[1, 0],).sort_index()

    data = (
        xr.Dataset.from_dataframe(data)
        .drop_vars(["new_cases", "new_deaths"])
        .rename({"total_cases": "cases", "total_deaths": "deaths"})
    )

    data.attrs["date"] = max_date(data)
    data.attrs["source_url"] = url
    data.attrs["source"] = "ECDC (Our World in Data)"

    return data


def excess_deaths_ft():
    """ Excess deaths from the FT.

        Note this is returned as a dataframe not an xarray, because it's slow and inefficient to
        turn into a dense xarray and sparse xarrays are not well supported.
    """
    url = (
        "https://raw.githubusercontent.com/Financial-Times/coronavirus-excess-mortality-data"
        "/master/data/ft_excess_deaths.csv"
    )
    data = pd.read_csv(
        url, index_col=["country", "region", "period", "date"], parse_dates=["date"]
    ).drop(columns=["year", "month", "week"]).sort_index()
    # data = xr.Dataset.from_dataframe(data)
    # data.attrs["date"] = max_date(data)
    # data.attrs["source_url"] = url
    # data.attrs["source"] = "Financial Times"

    return data
