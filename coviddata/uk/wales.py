import pandas as pd
import xarray as xr
from ..util import max_date

gss_lookup = {
    "Isle of Anglesey": "W06000001",
    "Gwynedd": "W06000002",
    "Conwy": "W06000003",
    "Denbighshire": "W06000004",
    "Flintshire": "W06000005",
    "Wrexham": "W06000006",
    "Ceredigion": "W06000008",
    "Pembrokeshire": "W06000009",
    "Carmarthenshire": "W06000010",
    "Swansea": "W06000011",
    "Neath Port Talbot": "W06000012",
    "Bridgend": "W06000013",
    "Vale of Glamorgan": "W06000014",
    "Cardiff": "W06000015",
    "Rhondda Cynon Taf": "W06000016",
    "Caerphilly": "W06000018",
    "Blaenau Gwent": "W06000019",
    "Torfaen": "W06000020",
    "Monmouthshire": "W06000021",
    "Newport": "W06000022",
    "Powys": "W06000023",
    "Merthyr Tydfil": "W06000024",
}


def cases(key="location"):
    """ Cases from the Welsh government.
    """
    #  TODO: is this URL dynamic? Maybe we need to scrape it from https://covid19-phwdata.nhs.wales/
    url = (
        "http://www2.nphs.wales.nhs.uk:8080/CommunitySurveillanceDocs.nsf/3dc04669c9e1eaa880257062003b246b/"
        "77fdb9a33544aee88025855100300cab/$FILE/Rapid%20COVID-19%20surveillance%20data.xlsx"
    )
    data = (
        pd.read_excel(url, sheet_name="Tests by specimen date")
        .drop(
            columns=[
                "Cases (new)",
                "Cumulative incidence per 100,000 population",
                "Testing episodes (new)",
            ]
        )
        .rename(
            columns={
                "Local Authority": "location",
                "Specimen date": "date",
                "Cumulative cases": "cases",
                "Cumulative testing episodes": "tests",
            }
        )
    )

    if key == "gss_code":
        data['gss_code'] = [gss_lookup.get(name) for name in data['location']]
        # Remove the "Unknown" and "Outside Wales" entries
        data = data[~data['gss_code'].isnull()]
        data = data.drop(columns=['location']).set_index(["gss_code", "date"])
    elif key == "location":
        data = data.set_index(["location", "date"])

    data = data.sort_index()
    data = xr.Dataset.from_dataframe(data)
    data.attrs[
        "source_url"
    ] = "https://covid19-phwdata.nhs.wales/"
    data.attrs["source"] = "Public Health Wales"
    data.attrs["date"] = max_date(data)
    return data
