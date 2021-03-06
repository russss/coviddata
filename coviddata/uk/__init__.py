from collections import defaultdict
from lxml.html import html5parser
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin
from datetime import date, timedelta
from io import StringIO
import logging
import requests
import json
import time
import numpy as np
import pandas as pd
import xarray as xr
from ..util import max_date

PHE_ENDPOINT = "https://api.coronavirus.data.gov.uk"

log = logging.getLogger(__name__)


def phe_query(filters={}, fields=[], fmt="csv", page=None):
    """ Helper to generate a query for the new PHE data API """

    params = {
        "filters": ";".join(f"{k}={v}" for k, v in filters.items()),
        "structure": json.dumps({f: f for f in fields}, separators=(",", ":")),
        "format": fmt,
    }

    if page is not None:
        params["page"] = page

    return "/v1/data?" + urlencode(params)


def phe_fetch_url(path):
    """Fetch a URL from the coronavirus.data.gov.uk API with elaborate retry
    handling because they can't operate a functional website.
    """
    url = PHE_ENDPOINT + path

    retry_count = 5
    while retry_count > 0:
        res = requests.get(url)

        if res.status_code in (200, 204):
            break
        elif 400 <= res.status_code < 500:
            res.raise_for_status()

        sleep_time = int(res.headers.get("Retry-After", 60))
        retry_count -= 1
        log.info(
            "PHE request (%s) failed with code %s. Waiting %s seconds "
            "(%s retries left)...",
            path,
            res.status_code,
            sleep_time,
            retry_count,
        )
        time.sleep(sleep_time)

    if retry_count == 0:
        raise Exception(f"PHE fetch ({path}) failed.")

    return res


def phe_fetch_csv(filters, fields):
    """ Fetch data from coronavirus.data.gov.uk as a CSV."""
    page = 1
    result_data = ""

    while True:
        path = phe_query(filters=filters, fields=fields, fmt="csv", page=page)
        res = phe_fetch_url(path)
        res.raise_for_status()

        if res.status_code == 204:
            break

        result_lines = res.text.split("\n")
        if page > 1:
            result_lines = result_lines[1:]
        result_data += "\n".join(result_lines)

        page += 1

    return StringIO(result_data)


def phe_fetch_json(filters, fields):
    """ Fetch data from coronavirus.data.gov.uk as JSON, returning a Pandas-compatible dict-of-lists."""
    start = time.time()
    log.debug("JSON Query: filters: %s  fields: %s", filters, fields)
    data = defaultdict(list)
    url = phe_query(filters=filters, fields=fields, fmt="json")
    while True:
        log.debug("- Fetching JSON page %s", url)
        res = phe_fetch_url(url)
        response = res.json()

        log.debug("- Returned %s records", len(response["data"]))
        for row in response["data"]:
            for key, val in row.items():
                data[key].append(val)

        if response["pagination"]["next"]:
            url = response["pagination"]["next"]
        else:
            break

    log.debug("Query complete, %s records in %.3f secs", len(data), time.time() - start)
    return data


def _fix_by(by):
    return {"countries": "nation", "regions": "region", "ltlas": "ltla"}.get(by, by)


def cases_phe(by="nation", key="name", basis="occurrence"):
    """Cases data from Public Health England.
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

    if basis == "occurrence":
        cases_field = "cumCasesBySpecimenDate"
    else:
        cases_field = "cumCasesByPublishDate"

    data = pd.DataFrame(
        phe_fetch_json(
            filters={"areaType": _fix_by(by)},
            fields=[loc_field, "date", cases_field],
        )
    )

    data["date"] = pd.to_datetime(data["date"])

    data = (
        data.rename(columns={cases_field: "cases", loc_field: loc_name})
        .set_index(["date", loc_name])
        .sort_index()
    )

    xdata = xr.Dataset.from_dataframe(data)
    xdata.attrs["date"] = max_date(xdata)
    xdata.attrs["source"] = "Public Health England"
    xdata.attrs["source_url"] = "https://coronavirus.data.gov.uk/"

    return xdata


def tests_phe():
    """ Data on number of tests carried out from Public Health England. """
    fields = [
        "date",
        "plannedCapacityByPublishDate",
        "capacityPillarOne",
        "capacityPillarTwo",
        "capacityPillarThree",
        "capacityPillarFour",
        "newPillarOneTestsByPublishDate",
        "newPillarTwoTestsByPublishDate",
        "newPillarThreeTestsByPublishDate",
        "newPillarFourTestsByPublishDate",
    ]
    data = pd.DataFrame(phe_fetch_json(filters={"areaType": "overview"}, fields=fields))
    data["date"] = pd.to_datetime(data["date"])
    data = data.set_index(["date"]).sort_index()

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
            "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/"
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
                engine="openpyxl",  # due to xlrd incompatibility with py3.9
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

    data = pd.DataFrame(
        phe_fetch_json(
            filters={"areaType": "nhsregion"},
            fields=[loc_field, "date", "cumAdmissions"],
        )
    )

    data["date"] = pd.to_datetime(data["date"])

    data = (
        data.rename(columns={loc_field: loc_name, "cumAdmissions": "admissions"})
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


def fetch_json_ld(url):
    res = requests.get(url)
    res.raise_for_status()
    root = html5parser.fromstring(res.text)
    return json.loads(
        root.find(
            './/{http://www.w3.org/1999/xhtml}script[@type="application/ld+json"]'
        ).text
    )


def infections_ons():
    res = requests.get(
        "https://www.ons.gov.uk/peoplepopulationandcommunity/healthandsocialcare/"
        "conditionsanddiseases/datasets/coronaviruscovid19infectionsurveydata"
    )
    root = html5parser.fromstring(res.text)
    url = urljoin(
        "https://www.ons.gov.uk",
        root.find(
            './/{http://www.w3.org/1999/xhtml}a[@aria-label="Download Coronavirus'
            ' (COVID-19) Infection Survey: 2020 in xlsx format"]'
        ).get("href"),
    )

    df = pd.read_excel(
        requests.get(url).content, sheet_name="2b", skiprows=6, skipfooter=10
    )
    df = df.drop(columns=[df.columns[4], df.columns[8]])
    df.columns = [
        "date",
        "incidence",
        "incidence_lower",
        "incidence_upper",
        "infections",
        "infections_lower",
        "infections_upper",
        "weekly",
        "weekly_lower",
        "weekly_upper",
    ]
    return df


def cases_by_age(area_type="ltla", key="gss_code", var="absolute"):
    data = pd.read_csv(
        "https://coronavirus.data.gov.uk/downloads/demographic/cases/specimenDate_ageDemographic-stacked.csv",
        parse_dates=["date"],
    )

    # 0-59 and 60+ overlap other age ranges, so we're not interested
    data = data[
        (data["areaType"] == area_type)
        & (data["age"] != "0_59")
        & (data["age"] != "60+")
    ]
    data = data.drop(columns=["areaType"])
    data["age"] = data["age"].str.replace(
        r"([0-9]+)_([0-9]+)", lambda r: r.group(1) + "-" + r.group(2)
    )

    if var == "absolute":
        data = data.drop(
            columns=[
                "newCasesBySpecimenDateRollingSum",
                "newCasesBySpecimenDateRollingRate",
            ]
        ).rename(columns={"newCasesBySpecimenDate": "cases"})
    elif var == "rate":
        data = data.drop(
            columns=[
                "newCasesBySpecimenDateRollingSum",
                "newCasesBySpecimenDate",
            ]
        ).rename(columns={"newCasesBySpecimenDateRollingRate": "rate"})

    if key == "gss_code":
        index_cols = ["gss_code"]
        data = data.drop(columns=["areaName"]).rename(columns={"areaCode": "gss_code"})
    elif key == "name":
        index_cols = ["name"]
        data = data.drop(columns=["areaCode"]).rename(columns={"areaName": "name"})

    index_cols += ["date", "age"]

    data = data.set_index(index_cols)
    data = xr.Dataset.from_dataframe(data)

    data.attrs["date"] = max_date(data)
    data.attrs["source"] = "Public Health England"
    data.attrs["source_url"] = "https://coronavirus.data.gov.uk/"
    return data


def test_positivity(area_type="ltla", key="gss"):
    """ 7-day test positivity """
    if key == "name":
        loc_field = "areaName"
        loc_name = "location"
    elif key == "gss":
        loc_field = "areaCode"
        loc_name = "gss_code"

    data = pd.DataFrame(
        phe_fetch_json(
            filters={"areaType": area_type},
            fields=[loc_field, "date", "uniqueCasePositivityBySpecimenDateRollingSum"],
        )
    )

    data["date"] = pd.to_datetime(data["date"])

    data = (
        data.rename(
            columns={
                loc_field: loc_name,
                "uniqueCasePositivityBySpecimenDateRollingSum": "positivity",
            }
        )
        .set_index([loc_name, "date"])
        .sort_index()
    )

    data = xr.Dataset.from_dataframe(data)

    data.attrs["date"] = max_date(data)
    data.attrs["source"] = "Public Health England"
    data.attrs["source_url"] = "https://coronavirus.data.gov.uk/"
    return data


def vaccinations():
    """ Fetch daily data (by date of report) on vaccinations.
        This dataset also includes some weekly date-of-vaccination
        data points from before the daily dataset started."""
    data = pd.DataFrame(
        phe_fetch_json(
            filters={"areaType": "overview"},
            fields=[
                "areaName",
                "date",
                "cumPeopleVaccinatedFirstDoseByPublishDate",
                "cumPeopleVaccinatedSecondDoseByPublishDate",
            ],
        )
    ).rename(columns={"cumPeopleVaccinatedFirstDoseByPublishDate": "first_dose",
                      "cumPeopleVaccinatedSecondDoseByPublishDate": "second_dose",
                      "areaName": "location"
                      }).drop(columns=['location'])

    data['date'] = pd.to_datetime(data['date'])
    data = data.set_index('date')

    # Insert values from weekly numbers before daily stats were available.
    data.loc[pd.to_datetime('2020-12-6')] = [0, 0]
    data.loc[pd.to_datetime('2020-12-7')] = [0, 0]
    data.loc[pd.to_datetime('2020-12-20')] = [663809, 0]
    data.loc[pd.to_datetime('2020-12-27')] = [985479, 0]
    data.loc[pd.to_datetime('2021-01-03')] = [1344152, 20977]

    data = xr.Dataset.from_dataframe(data.sort_index())

    data.attrs["date"] = max_date(data)
    data.attrs["source"] = "Public Health England"
    data.attrs["source_url"] = "https://coronavirus.data.gov.uk/"
    return data
