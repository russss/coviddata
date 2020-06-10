from collections import defaultdict
from lxml.html import html5parser
from dateutil.parser import parse as parse_date
from urllib.error import HTTPError
from datetime import date, timedelta
import requests
import numpy as np
import pandas as pd
import xarray as xr
from .util import max_date


def cases_phe(by="countries"):
    """ Cases and deaths data from Public Health England.
        This is the data used by coronavirus.data.gov.uk.

        The `by` variable can be "countries", "regions", "utlas", or "ltlas".
    """
    url = f"https://c19downloads.azureedge.net/downloads/data/{by}_latest.json"

    res = requests.get(url)
    res.raise_for_status()
    data = res.json()

    series = []
    for gss, area_data in data.items():
        if gss == "metadata":
            continue
        name = area_data["name"]["value"]
        converted = defaultdict(dict)

        if "dailyTotalConfirmedCases" in area_data:
            for val in area_data["dailyTotalConfirmedCases"]:
                converted[val["date"]]["cases"] = val["value"]

        if "changeInDailyCasesAdjusted" in area_data:
            for val in area_data["changeInDailyCasesAdjusted"]:
                converted[val["date"]]["new_cases"] = val["value"]

        if "dailyTotalDeaths" in area_data:
            for val in area_data["dailyTotalDeaths"]:
                converted[val["date"]]["deaths"] = val["value"]

        for d, value in converted.items():
            row = {"date": parse_date(d), "location": name, "gss_code": gss}
            if "cases" in value:
                row["cases"] = value["cases"]
            if "new_cases" in value:
                row["new_cases"] = value["new_cases"]
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


def deaths_nhs():
    def col_sel(name):
        if type(name) == str and "Unnamed" in name:
            return False
        return True

    today = date.today()

    i = 0
    while True:
        url = (
            f"https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/"
            f"{today.year}/{today.month:02}/"
            f"COVID-19-total-announced-deaths-{today.day}-{today.strftime('%B-%Y')}.xlsx"
        )
        try:
            data = pd.read_excel(
                url,
                sheet_name="Tab1 Deaths by region",
                skiprows=15,
                usecols=col_sel,
                index_col=0,
            )
            break
        except HTTPError:
            if i == 4:
                raise
            today -= timedelta(days=1)
            i += 1

    data = pd.DataFrame(
        data.drop([np.nan, "England"])
        .drop(columns=["Up to 01-Mar-20", "Awaiting verification", "Total"])
        .unstack()
    ).reset_index()

    data = data.rename(
        columns={0: "deaths", "level_0": "date", "NHS England Region": "location"}
    ).set_index(["date", "location"])

    data = data.rename(
        {
            "East Of England": "East of England",
            "North East And Yorkshire": "North East and Yorkshire",
        }
    )

    data = xr.Dataset.from_dataframe(data)
    data.attrs["date"] = today
    data.attrs["source"] = "NHS England"
    data.attrs["source_url"] = url

    return data


def _latest_press_conference_data():
    """ Fetch the URL for the latest government press conference Excel dataset.

        This is a complete shitshow made only fractionally less ridiculous by the gov.uk content API.
    """
    index_url = (
        "https://www.gov.uk/api/content/government/collections"
        "/slides-and-datasets-to-accompany-coronavirus-press-conferences"
    )

    res = requests.get(index_url)
    res.raise_for_status()
    index_data = res.json()

    docs = sorted(
        [
            doc
            for doc in index_data["links"]["documents"]
            if doc["title"].startswith("Slides and datasets")
        ],
        key=lambda doc: doc["public_updated_at"],
    )

    res = requests.get(docs[-1]["api_url"])
    res.raise_for_status()
    doc_data = res.json()

    spreadsheets = [
        att
        for att in doc_data["details"]["attachments"]
        if att["content_type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]

    if len(spreadsheets) != 1:
        raise ValueError(f"No spreadsheet found in {docs[-1]['api_url']}")

    return (
        spreadsheets[0]["url"],
        "https://www.gov.uk" + doc_data["base_path"],
        parse_date(doc_data["public_updated_at"]),
    )


def people_in_hospital():
    url, source, publish_date = _latest_press_conference_data()
    data = pd.read_excel(
        url, sheet_name="People in Hospital (UK)", parse_date=["Date"], skiprows=4,
    )

    data = (
        data[~data.Date.str.startswith("(").fillna(False)]
        .set_index("Date")
        .unstack()
        .to_frame()
        .rename(columns={0: "patients"})
    )
    data.index.names = ["location", "date"]

    data = data.rename({"North East & Yorkshire": "North East and Yorkshire"})

    data = xr.Dataset.from_dataframe(data)
    data.attrs["date"] = publish_date
    data.attrs['source'] = 'UK Government Press Conference'
    data.attrs['source_url'] = source
    return data
