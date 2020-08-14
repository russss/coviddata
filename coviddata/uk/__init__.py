from collections import defaultdict
from lxml.html import html5parser
from dateutil.parser import parse as parse_date
from urllib.error import HTTPError
from urllib.parse import urlencode
from datetime import date, timedelta
from io import StringIO
import requests
import json
import numpy as np
import pandas as pd
import xarray as xr
from ..util import max_date


def phe_query(filters={}, fields=[], fmt="csv", page=None):
    """ Helper to generate a query for the new PHE data API """
    endpoint = "https://api.coronavirus.data.gov.uk/v1/data"

    params = {
            "filters": ";".join(f"{k}={v}" for k, v in filters.items()),
            "structure": json.dumps({f: f for f in fields}, separators=(",", ":")),
            "format": fmt,
        }

    if page is not None:
        params['page'] = page

    return endpoint + "?" + urlencode(params)


def phe_fetch_csv(filters, fields):
    page = 1
    result_data = ''

    while True:
        url = phe_query(filters=filters, fields=fields, fmt='csv', page=page)
        res = requests.get(url)
        res.raise_for_status()

        if res.status_code == 204:
            break

        result_lines = res.text.split("\n")
        if page > 1:
            result_lines = result_lines[1:]
        result_data += "\n".join(result_lines)

        page += 1

    return StringIO(result_data)


def _fix_by(by):
    return {'countries': 'nation',
             'regions': 'region',
             'ltlas': 'ltla'}.get(by, by)


def cases_phe(by="nation", key="name", basis="occurrence"):
    """ Cases data from Public Health England.
        This is the data used by coronavirus.data.gov.uk.

        The `by` variable can be "nation", "region", or "ltla".

        The `key` variable can be "name" if you want the data broken down by
        location name, or "gss_code" for GSS code.

        The `basis` variable can be "occurrence" to retrieve cases by date of
        sample and deaths by date of death, or "report" to fetch them by date
        of report. Note that Northern Ireland does not provide data by date of occurrence.
    """
    if key == "name":
        loc_field = "areaName"
        loc_name = "location"
    elif key == "gss_code":
        loc_field = "areaCode"
        loc_name = "gss_code"

    if basis == 'occurrence':
        cases_field = "cumCasesBySpecimenDate"
    else:
        cases_field = "cumCasesByPublishDate"

    data = phe_fetch_csv(
        filters={"areaType": _fix_by(by)},
        fields=[loc_field, "date", cases_field],
    )

    data = pd.read_csv(data, parse_dates=['date'], dayfirst=True).rename(columns={
        cases_field: "cases",
        loc_field: loc_name
    }).set_index(["date", loc_name])

    xdata = xr.Dataset.from_dataframe(data)
    xdata.attrs["date"] = max_date(xdata)
    xdata.attrs["source"] = "Public Health England"
    xdata.attrs["source_url"] = "https://coronavirus.data.gov.uk/"

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
    url = _get_nhs_potential("111 Online Potential COVID-19 Open Data")
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
        if today == date(2020, 7, 11):
            url = url.replace(".xlsx", "-1.xlsx")

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


def hospitalisations_phe(key="name"):
    if key == "name":
        loc_field = "areaName"
        loc_name = "location"
    elif key == "gss":
        loc_field = "areaCode"
        loc_name = "gss_code"

    data = phe_fetch_csv(
        filters={"areaType": "nhsregion"}, fields=[loc_field, "date", "cumAdmissions"],
    )

    data = (
        pd.read_csv(data, parse_dates=["date"])
        .rename(columns={loc_field: loc_name, "cumAdmissions": "admissions"})
        .set_index([loc_name, "date"])
        .sort_index()
    )
    data = xr.Dataset.from_dataframe(data)
    data.attrs["date"] = max_date(data)
    data.attrs["source"] = "Public Health England"
    data.attrs["source_url"] = "https://coronavirus.data.gov.uk/"

    data = data.ffill("date")  # Fill-forward missing data
    return data


def deaths_phe(key="name"):
    if key == "name":
        loc_field = "areaName"
        loc_name = "location"
    elif key == "gss":
        loc_field = "areaCode"
        loc_name = "gss_code"

    data = phe_fetch_csv(
        filters={"areaType": "nation"},
        fields=[loc_field, "date", "cumDeathsByDeathDate"],
    )
    data = (
        pd.read_csv(data, parse_dates=["date"])
        .rename(columns={"cumDeathsByDeathDate": "deaths", loc_field: loc_name})
        .set_index([loc_name, "date"])
        .sort_index()
    )
    data = xr.Dataset.from_dataframe(data)
    data.attrs["date"] = max_date(data)
    data.attrs["source"] = "Public Health England"
    data.attrs["source_url"] = "https://coronavirus.data.gov.uk/"

    data = data.ffill("date")  # Fill-forward missing data
    return data
