from lxml.html import html5parser
import requests
import pandas as pd
import xarray as xr
from .util import max_date


def cases_phe():
    url = "https://www.arcgis.com/sharing/rest/content/items/e5fd11150d274bebaaf8fe2a7a2bda11/data"
    uk_data = (
        pd.read_excel(url, parse_dates=[0],)
        .rename(columns={"DateVal": "date", "CumCases": "cases", "CumDeaths": "deaths"})
        .drop(columns=["CMODateCount", "DailyDeaths"])
        .set_index("date")
        .sort_index()
    )

    data = xr.Dataset.from_dataframe(uk_data).expand_dims(
        {"location": ["United Kingdom"]}
    )
    data.attrs["date"] = max_date(data)
    data.attrs["source"] = "Public Health England"
    data.attrs["source_url"] = url

    return data


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
