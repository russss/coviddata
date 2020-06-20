import pandas as pd
import xarray as xr
from .util import max_date


def cases_ecdc(by="name"):
    """ Reported cases and deaths from the European Centre for Disease Control.

        The "by" parameter can be "name" for country name or "iso3" for 3-digit ISO code.
    """
    url = "https://opendata.ecdc.europa.eu/covid19/casedistribution/csv"
    data = (
        pd.read_csv(url, parse_dates=[0], dayfirst=True)
        .drop(["day", "month", "year", "popData2019", "geoId", "continentExp"], axis=1)
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

    if by == "name":
        data = data.set_index(["location", "date"]).drop(columns=["iso3"])
    elif by == "iso3":
        data = data.set_index(["iso3", "date"]).drop(columns=["location"])

    data = data.sort_index()

    # Remove duplicates, because I've seen them occur
    data = data.loc[~data.index.duplicated(keep="first")]

    data = xr.Dataset.from_dataframe(data)

    # Make numbers cumulative to match other datasets
    data["deaths"] = data["deaths"].cumsum(dim="date")
    data["cases"] = data["cases"].cumsum(dim="date")

    data.attrs["date"] = max_date(data)
    data.attrs["source_url"] = url
    data.attrs["source"] = "ECDC"
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
    data = (
        pd.read_csv(
            url, index_col=["country", "region", "period", "date"], parse_dates=["date"]
        )
        .drop(columns=["year", "month", "week"])
        .sort_index()
    )
    # data = xr.Dataset.from_dataframe(data)
    # data.attrs["date"] = max_date(data)
    # data.attrs["source_url"] = url
    # data.attrs["source"] = "Financial Times"

    return data
