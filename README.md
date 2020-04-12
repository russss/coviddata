# COVIDdata

Yet another python package for accessing COVID-19 data. Sorry. I have opinions and I don't like all the others.

This package provides methods for fetching various COVID-19 related data sources. Results are provided as [xarray](http://xarray.pydata.org/) datasets, with consistent variable naming and attribution data included.

## Installation

I'm not going to clutter PyPI up with yet another COVID package. Just do `pip install git+https://github.com/russs/coviddata#egg=coviddata`.


## Worldwide Data

My preferred wordwide data source is [Our World in Data](https://ourworldindata.org/coronavirus-source-data) which sources their data from the ECDC. The `cases_owid` function downloads this data and returns a Dataset.


```python
import coviddata.world
world_cases = coviddata.world.cases_owid()
world_cases
```




<pre>&lt;xarray.Dataset&gt;
Dimensions:   (date: 104, location: 207)
Coordinates:
  * location  (location) object &#x27;Afghanistan&#x27; &#x27;Albania&#x27; ... &#x27;Zambia&#x27; &#x27;Zimbabwe&#x27;
  * date      (date) datetime64[ns] 2019-12-31 2020-01-01 ... 2020-04-12
Data variables:
    cases     (location, date) float64 0.0 0.0 0.0 0.0 ... 11.0 11.0 11.0 14.0
    deaths    (location, date) float64 0.0 0.0 0.0 0.0 0.0 ... 2.0 3.0 3.0 3.0
Attributes:
    date:        2020-04-12
    source_url:  https://cowid.netlify.com/data/ecdc/full_data.csv
    source:      ECDC (Our World in Data)</pre>



We can filter this data by country, and convert it to a [pandas](https://pandas.pydata.org/) dataframe, giving us easy access to pandas' plotting functions.


```python
import matplotlib
matplotlib.rcParams['figure.figsize'] = [14, 6]

(world_cases.sel(location="United States")
     .to_dataframe()
     .plot(logy=True, title="US COVID-19 Cases & Deaths"))
```




    <matplotlib.axes._subplots.AxesSubplot at 0x12a0522d0>




![png](README_files/README_3_1.png)


## Country-specific Data

Some country-specific data sources are more reliable or complete.

UK data can be fetched from [Public Health England](https://www.gov.uk/government/publications/covid-19-track-coronavirus-cases), and US data from the [Covid Tracking Project](https://covidtracking.com/):


```python
import coviddata.uk
uk_cases = coviddata.uk.cases_phe()
uk_cases
```




<pre>&lt;xarray.Dataset&gt;
Dimensions:   (date: 73, location: 1)
Coordinates:
  * location  (location) &lt;U14 &#x27;United Kingdom&#x27;
  * date      (date) datetime64[ns] 2020-01-31 2020-02-01 ... 2020-04-12
Data variables:
    cases     (location, date) int64 2 2 2 2 2 ... 60733 65077 70272 74895 79345
    deaths    (location, date) float64 nan nan nan ... 9.875e+03 1.061e+04
Attributes:
    date:        2020-04-12
    source:      Public Health England
    source_url:  https://www.arcgis.com/sharing/rest/content/items/e5fd11150d...</pre>




```python
import coviddata.us
us_cases = coviddata.us.cases_covidtracking()
us_cases
```




<pre>&lt;xarray.Dataset&gt;
Dimensions:   (date: 44, location: 1)
Coordinates:
  * location  (location) &lt;U13 &#x27;United States&#x27;
  * date      (date) datetime64[ns] 2020-02-28 2020-02-29 ... 2020-04-11
Data variables:
    cases     (location, date) int64 9 18 31 35 ... 424289 458635 493252 522843
    deaths    (location, date) int64 4 5 8 11 14 ... 14547 16424 18488 20355
    tests     (location, date) int64 9 18 31 35 ... 2375355 2529282 2665666
Attributes:
    date:        2020-04-11
    source:      COVID Tracking Project
    source_url:  http://covidtracking.com/api/us/daily.csv</pre>



## Merging

There's also a function to allow you quickly to combine these sources together:


```python
from coviddata import merge

combined_cases = merge(world_cases, uk_cases, us_cases)
combined_cases
```




<pre>&lt;xarray.Dataset&gt;
Dimensions:   (date: 104, location: 207)
Coordinates:
  * date      (date) datetime64[ns] 2019-12-31 2020-01-01 ... 2020-04-12
  * location  (location) object &#x27;Afghanistan&#x27; &#x27;Albania&#x27; ... &#x27;Zambia&#x27; &#x27;Zimbabwe&#x27;
Data variables:
    cases     (location, date) float64 0.0 0.0 0.0 0.0 ... 11.0 11.0 11.0 14.0
    deaths    (location, date) float64 0.0 0.0 0.0 0.0 0.0 ... 2.0 3.0 3.0 3.0
    tests     (location, date) float64 nan nan nan nan nan ... nan nan nan nan
Attributes:
    source:      [&#x27;ECDC (Our World in Data)&#x27;, &#x27;Public Health England&#x27;, &#x27;COVID...
    source_url:  [&#x27;https://cowid.netlify.com/data/ecdc/full_data.csv&#x27;, &#x27;https...
    date:        [datetime.date(2020, 4, 12), datetime.date(2020, 4, 12), dat...</pre>




```python
(combined_cases.sum(dim='location')
     .to_dataframe()
     .drop(columns=['tests'])
     .plot(logy=True, title="Worldwide COVID-19 Cases & Deaths"))
```




    <matplotlib.axes._subplots.AxesSubplot at 0x12a15f050>




![png](README_files/README_9_1.png)


## UK NHS Triage Data

The NHS [publishes statistics](https://digital.nhs.uk/data-and-information/publications/statistical/mi-potential-covid-19-symptoms-reported-through-nhs-pathways-and-111-online) on the number of COVID-19 triage decisions made over 999, 111, and 111 Online.

These functions are dependent on screen-scraping the NHS website and may be more unreliable.


```python
nhs_pathways = coviddata.uk.triage_nhs_pathways()
nhs_pathways
```




<pre>&lt;xarray.Dataset&gt;
Dimensions:    (age_band: 3, ccg: 229, date: 22, sex: 3, site_type: 2)
Coordinates:
  * date       (date) datetime64[ns] 2020-03-18 2020-03-19 ... 2020-04-08
  * age_band   (age_band) object &#x27;0-18 years&#x27; &#x27;19-69 years&#x27; &#x27;70-120 years&#x27;
  * ccg        (ccg) object &#x27;E38000001&#x27; &#x27;E38000002&#x27; ... &#x27;ZC030&#x27; &#x27;ZC040&#x27;
  * site_type  (site_type) int64 111 999
  * sex        (sex) object &#x27;Female&#x27; &#x27;Male&#x27; &#x27;Unknown&#x27;
    ccg_name   (date, age_band, ccg, site_type, sex) object &#x27;NHS Airedale, Wharfedale and Craven CCG&#x27; ... nan
Data variables:
    count      (date, age_band, ccg, site_type, sex) float64 8.0 6.0 ... nan nan
Attributes:
    date:        2020-04-08
    source:      NHS England
    source_url:  https://files.digital.nhs.uk/41/581BEE/NHS%20Pathways%20Covi...</pre>




```python
nhs_online = coviddata.uk.triage_nhs_online()
nhs_online
```




<pre>&lt;xarray.Dataset&gt;
Dimensions:   (age_band: 3, ccg: 209, date: 22, sex: 2)
Coordinates:
  * date      (date) datetime64[ns] 2020-03-18 2020-03-19 ... 2020-04-08
  * age_band  (age_band) object &#x27;0-18 years&#x27; &#x27;19-69 years&#x27; &#x27;70+ years&#x27;
  * ccg       (ccg) object &#x27;E38000001&#x27; &#x27;E38000002&#x27; ... &#x27;E38000247&#x27; &#x27;E38000248&#x27;
  * sex       (sex) object &#x27;Female&#x27; &#x27;Male&#x27;
    ccg_name  (date, age_band, ccg, sex) object &#x27;NHS Airedale, Wharfedale and Craven CCG&#x27; ... &#x27;NHS West Sussex CCG&#x27;
Data variables:
    count     (date, age_band, ccg, sex) float64 17.0 16.0 27.0 ... 6.0 7.0 12.0
Attributes:
    date:        2020-04-08
    source:      NHS England
    source_url:  https://files.digital.nhs.uk/BB/32CB5C/111%20Online%20Covid-...</pre>




```python
import matplotlib.pyplot as plt
ax = plt.axes()
(nhs_pathways.sum(['age_band', 'ccg', 'sex', 'site_type'])
     .to_dataframe()
     .plot(ax=ax, label='Pathways', y='count'))

(nhs_online.sum(['age_band', 'ccg', 'sex'])
     .to_dataframe()
     .plot(ax=ax, label='Online', y='count'))

plt.title("NHS COVID-19 Triage Rate")
plt.ylim(0)
```




    (0.0, 153673.3)




![png](README_files/README_13_1.png)

