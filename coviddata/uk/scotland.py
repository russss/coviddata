from datetime import date
import xarray as xr

from ..util import read_csv


def cases(key="location"):
    """ Cases from the Scottish government.

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
        data.gss_code = data.gss_code.str.replace('http://statistics.gov.scot/id/statistical-geography/', '')
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
    data.attrs["date"] = date.today()
    return data
