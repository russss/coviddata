from datetime import date, datetime
import requests
import pandas as pd
import xarray as xr

from ..util import read_csv, max_date


def cases(key="location"):
    """Cases from the Scottish government.

    Key can be "location" or "gss_code"
    """
    url = "https://statistics.gov.scot/slice/observations.csv?&dataset=http%3A%2F%2Fstatistics.gov.scot%2Fdata%2Fcoronavirus-covid-19-management-information&http%3A%2F%2Fpurl.org%2Flinked-data%2Fcube%23measureType=http%3A%2F%2Fstatistics.gov.scot%2Fdef%2Fmeasure-properties%2Fcount&http%3A%2F%2Fstatistics.gov.scot%2Fdef%2Fdimension%2Fvariable=http%3A%2F%2Fstatistics.gov.scot%2Fdef%2Fconcept%2Fvariable%2Ftesting-cumulative-people-tested-for-covid-19-positive"
    data = (
        read_csv(url, skiprows=7)
        .rename(
            columns={
                "Reference Area": "location",
                "http://purl.org/linked-data/sdmx/2009/dimension#refArea": "gss_code",
            }
        )
        .replace({"*": 0})
    )

    if key == "location":
        data = data.drop(columns="gss_code").set_index("location")
    elif key == "gss_code":
        data.gss_code = data.gss_code.str.replace(
            "http://statistics.gov.scot/id/statistical-geography/", ""
        )
        data = data.drop(columns="location").set_index("gss_code")

    data = (
        data.unstack()
        .to_frame()
        .reset_index()
        .rename(columns={"level_0": "date", 0: "cases"})
        .astype({"date": "datetime64[ns]", "cases": "float64"})
        .set_index([key, "date"])
    )
    data = xr.Dataset.from_dataframe(data)
    data.attrs[
        "source_url"
    ] = "https://statistics.gov.scot/resource?uri=http%3A%2F%2Fstatistics.gov.scot%2Fdata%2Fcoronavirus-covid-19-management-information"
    data.attrs["source"] = "Scottish Government"
    data.attrs["date"] = max_date(data)
    return data


def cases_by_la():
    """ Cases in Scotland by local authority GSS code"""
    base = "https://www.opendata.nhs.scot"
    url = "/api/3/action/datastore_search?resource_id=427f9a25-db22-4014-a3bc-893b68243055&limit=1000"

    records = []
    while True:
        res = requests.get(base + url)
        data = res.json()
        if len(data["result"]["records"]) == 0:
            break
        for record in data["result"]["records"]:
            records.append(
                [
                    datetime.strptime(str(record["Date"]), "%Y%m%d").date(),
                    record["CA"],
                    record["CumulativePositive"],
                    record["CumulativeNegative"],
                    record["CumulativeDeaths"],
                ]
            )
        url = data["result"]["_links"]["next"]

    df = (
        pd.DataFrame(records, columns=["date", "gss_code", "cases", "negatives", "deaths"])
        .set_index(["gss_code", "date"])
        .sort_index()
    )
    data = xr.Dataset.from_dataframe(df)
    data.attrs['source_url'] = base
    data.attrs['source'] = 'Public Health Scotland'
    data.attrs['date'] = max_date(data)
    return data
