from collections import defaultdict
from lxml.html import html5parser
from dateutil.parser import parse as parse_date
import requests
import pandas as pd
import xarray as xr
from .util import max_date


def cases_phe(by="countries"):
    url = f"https://c19downloads.azureedge.net/downloads/data/{by}_latest.json"

    res = requests.get(url)
    res.raise_for_status()
    data = res.json()

    series = []
    for gss, area_data in data.items():
        if gss == 'metadata':
            continue
        name = area_data["name"]["value"]
        converted = defaultdict(dict)
        if "dailyTotalConfirmedCases" in area_data:
            for val in area_data["dailyTotalConfirmedCases"]:
                converted[val["date"]]["cases"] = val["value"]

        if "dailyTotalDeaths" in area_data:
            for val in area_data["dailyTotalDeaths"]:
                converted[val["date"]]["deaths"] = val["value"]

        for date, value in converted.items():
            row = {"date": parse_date(date), "location": name, "gss_code": gss}
            if "cases" in value:
                row["cases"] = value["cases"]
            if "deaths" in value:
                row["deaths"] = value["deaths"]
            series.append(row)
    df = pd.DataFrame(series).set_index(["location", "date"])
    xdata = xr.Dataset.from_dataframe(df).set_coords(["gss_code"])
    xdata.attrs["date"] = max_date(xdata)
    xdata.attrs["source"] = "Public Health England"
    xdata.attrs["source_url"] = url

    return xdata


def _get_nhs_potential(title):
    url = (
        "https://digital.nhs.uk/data-and-information/publications/statistical"
        "/mi-potential-covid-19-symptoms-reported-through-nhs-pathways-and-111-online/latest"
    )

    text = requests.get(url).text
    et = html5parser.fromstring(text)

    el = et.find('.//{http://www.w3.org/1999/xhtml}a[@title="' + title + '"]')
    return el.get("href")


def triage_nhs_pathways():
    url = _get_nhs_potential("NHS Pathways Potential COVID-19 Open Data")
    df = (
        pd.read_csv(url, parse_dates=[1], dayfirst=True)
        .rename(
            columns={
                "SiteType": "site_type",
                "Call Date": "date",
                "Sex": "sex",
                "AgeBand": "age_band",
                "CCGCode": "ccg",
                "CCGName": "ccg_name",
                "TriageCount": "count",
            }
        )
        .set_index(["date", "age_band", "ccg", "site_type", "sex"])
    )

    data = xr.Dataset.from_dataframe(df).set_coords(["ccg_name"])
    data.attrs["date"] = max_date(data)
    data.attrs["source"] = "NHS England"
    data.attrs["source_url"] = url
    return data


def triage_nhs_online():
    url = _get_nhs_potential("111 Online Potential COIVD-19 Open Data")
    df = (
        pd.read_csv(url, parse_dates=[0], dayfirst=True)
        .rename(
            columns={
                "journeydate": "date",
                "ageband": "age_band",
                "ccgcode": "ccg",
                "ccgname": "ccg_name",
                "Total": "count",
            }
        )
        .set_index(["date", "age_band", "ccg", "sex"])
    )

    data = xr.Dataset.from_dataframe(df).set_coords(["ccg_name"])
    data.attrs["date"] = max_date(data)
    data.attrs["source"] = "NHS England"
    data.attrs["source_url"] = url
    return data
