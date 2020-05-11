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
Dimensions:   (date: 133, location: 210)
Coordinates:
  * location  (location) object &#x27;Afghanistan&#x27; &#x27;Albania&#x27; ... &#x27;Zambia&#x27; &#x27;Zimbabwe&#x27;
  * date      (date) datetime64[ns] 2019-12-31 2020-01-01 ... 2020-05-11
Data variables:
    cases     (location, date) float64 0.0 0.0 0.0 0.0 ... 34.0 35.0 36.0 36.0
    deaths    (location, date) float64 0.0 0.0 0.0 0.0 0.0 ... 4.0 4.0 4.0 4.0
Attributes:
    date:        2020-05-11
    source_url:  https://cowid.netlify.com/data/ecdc/full_data.csv
    source:      ECDC (Our World in Data)</pre>



We can filter this data by country, and convert it to a [pandas](https://pandas.pydata.org/) dataframe, giving us easy access to pandas' plotting functions.


```python
import matplotlib
matplotlib.rcParams['figure.figsize'] = [14, 6]

(world_cases.sel(location="United States")
     .to_dataframe()
     .plot(logy=True, title="US COVID-19 Cases & Deaths"));
```


![png](README_files/README_3_0.png)


## Country-specific Data

Some country-specific data sources are more reliable or complete.

### UK Cases Data

UK data can be fetched from [Public Health England](https://www.gov.uk/government/publications/covid-19-track-coronavirus-cases). Note that:

* This data is broken down by constituent UK country whereas global data is usually combined.
* The cases data is a subset of total UK cases - [more info](https://coronavirus.data.gov.uk/about)


```python
import coviddata.uk
uk_cases = coviddata.uk.cases_phe()
uk_cases
```




<pre>&lt;xarray.Dataset&gt;
Dimensions:   (date: 92, location: 4)
Coordinates:
  * location  (location) object &#x27;England&#x27; &#x27;Northern Ireland&#x27; &#x27;Scotland&#x27; &#x27;Wales&#x27;
  * date      (date) datetime64[ns] 2020-01-30 2020-01-31 ... 2020-05-10
    gss_code  (location, date) object &#x27;E92000001&#x27; &#x27;E92000001&#x27; ... &#x27;W92000004&#x27;
Data variables:
    cases     (location, date) float64 1.0 2.0 8.0 9.0 12.0 ... nan nan nan nan
    deaths    (location, date) float64 nan nan nan ... 1.099e+03 1.111e+03
Attributes:
    date:        2020-05-10
    source:      Public Health England
    source_url:  https://c19downloads.azureedge.net/downloads/data/countries_...</pre>



### US Data

US data from the [Covid Tracking Project](https://covidtracking.com/):


```python
import coviddata.us
us_cases = coviddata.us.cases_covidtracking()
us_cases
```




<pre>&lt;xarray.Dataset&gt;
Dimensions:   (date: 110, location: 1)
Coordinates:
  * location  (location) &lt;U13 &#x27;United States&#x27;
  * date      (date) datetime64[ns] 2020-01-22 2020-01-23 ... 2020-05-10
Data variables:
    cases     (location, date) int64 1 1 1 1 ... 1248137 1275916 1301095 1322807
    deaths    (location, date) float64 nan nan nan ... 7.329e+04 7.427e+04
    tests     (location, date) int64 1 1 1 1 ... 8105513 8408788 8709630 8987524
Attributes:
    date:        2020-05-10
    source:      COVID Tracking Project
    source_url:  http://covidtracking.com/api/us/daily.csv</pre>



## Merging

There's also a function to allow you quickly to combine these sources together:


```python
from coviddata import merge

combined_cases = merge(world_cases, us_cases)
combined_cases
```




<pre>&lt;xarray.Dataset&gt;
Dimensions:   (date: 133, location: 210)
Coordinates:
  * date      (date) datetime64[ns] 2019-12-31 2020-01-01 ... 2020-05-11
  * location  (location) object &#x27;Afghanistan&#x27; &#x27;Albania&#x27; ... &#x27;Zambia&#x27; &#x27;Zimbabwe&#x27;
Data variables:
    cases     (location, date) float64 0.0 0.0 0.0 0.0 ... 34.0 35.0 36.0 36.0
    deaths    (location, date) float64 0.0 0.0 0.0 0.0 0.0 ... 4.0 4.0 4.0 4.0
    tests     (location, date) float64 nan nan nan nan nan ... nan nan nan nan
Attributes:
    source:      [&#x27;ECDC (Our World in Data)&#x27;, &#x27;COVID Tracking Project&#x27;]
    source_url:  [&#x27;https://cowid.netlify.com/data/ecdc/full_data.csv&#x27;, &#x27;http:...
    date:        [datetime.date(2020, 5, 11), datetime.date(2020, 5, 10)]</pre>




```python
(combined_cases.sum(dim='location')
     .to_dataframe()
     .drop(columns=['tests'])
     .plot(logy=True, title="Worldwide COVID-19 Cases & Deaths"))
```




    <matplotlib.axes._subplots.AxesSubplot at 0x12c2c6c10>




![png](README_files/README_10_1.png)


## UK NHS Triage Data

The NHS [publishes statistics](https://digital.nhs.uk/data-and-information/publications/statistical/mi-potential-covid-19-symptoms-reported-through-nhs-pathways-and-111-online) on the number of COVID-19 triage decisions made over 999, 111, and 111 Online.

These functions are dependent on screen-scraping the NHS website and may be more unreliable.


```python
nhs_pathways = coviddata.uk.triage_nhs_pathways()
nhs_pathways
```




<pre>&lt;xarray.Dataset&gt;
Dimensions:    (age_band: 3, ccg: 236, date: 54, sex: 3, site_type: 2)
Coordinates:
  * date       (date) datetime64[ns] 2020-03-18 2020-03-19 ... 2020-05-10
  * age_band   (age_band) object &#x27;0-18 years&#x27; &#x27;19-69 years&#x27; &#x27;70-120 years&#x27;
  * ccg        (ccg) object &#x27;E38000001&#x27; &#x27;E38000002&#x27; ... &#x27;ZC030&#x27; &#x27;ZC040&#x27;
  * site_type  (site_type) int64 111 999
  * sex        (sex) object &#x27;Female&#x27; &#x27;Male&#x27; &#x27;Unknown&#x27;
    ccg_name   (date, age_band, ccg, site_type, sex) object &#x27;NHS Airedale, Wharfedale and Craven CCG&#x27; ... nan
Data variables:
    count      (date, age_band, ccg, site_type, sex) float64 8.0 6.0 ... nan nan
Attributes:
    date:        2020-05-10
    source:      NHS England
    source_url:  https://files.digital.nhs.uk/5F/C91A7A/NHS%20Pathways%20Covi...</pre>




```python
nhs_online = coviddata.uk.triage_nhs_online()
nhs_online
```




<pre>&lt;xarray.Dataset&gt;
Dimensions:   (age_band: 3, ccg: 209, date: 54, sex: 2)
Coordinates:
  * date      (date) datetime64[ns] 2020-03-18 2020-03-19 ... 2020-05-10
  * age_band  (age_band) object &#x27;0-18 years&#x27; &#x27;19-69 years&#x27; &#x27;70+ years&#x27;
  * ccg       (ccg) object &#x27;E38000001&#x27; &#x27;E38000002&#x27; ... &#x27;E38000247&#x27; &#x27;E38000248&#x27;
  * sex       (sex) object &#x27;Female&#x27; &#x27;Male&#x27;
    ccg_name  (date, age_band, ccg, sex) object &#x27;NHS Airedale, Wharfedale and Craven CCG&#x27; ... &#x27;NHS West Sussex CCG&#x27;
Data variables:
    count     (date, age_band, ccg, sex) float64 17.0 16.0 27.0 ... 2.0 3.0 4.0
Attributes:
    date:        2020-05-10
    source:      NHS England
    source_url:  https://files.digital.nhs.uk/DA/564752/111%20Online%20Covid-...</pre>




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
plt.show()
```


![png](README_files/README_14_0.png)


## Interventions

List of interventions used by the Imperial College London model, in a reasonably simple format:


```python
import coviddata.interventions

coviddata.interventions.imperial_interventions()
```




<pre>&lt;xarray.Dataset&gt;
Dimensions:   (location: 83)
Coordinates:
  * location  (location) object &#x27;Austria&#x27; &#x27;Austria&#x27; ... &#x27;Netherlands&#x27;
    date      (location) datetime64[ns] 2020-03-14 2020-03-10 ... 2020-03-12
Data variables:
    type      (location) object &#x27;Schools + Universities&#x27; ... &#x27;Advice to work from home&#x27;
    event     (location) object &#x27;Nationwide school closures.&#x27; ... nan
Attributes:
    date:        2020-05-11 11:50:10.373939
    source:      Imperial College London
    source_url:  https://raw.githubusercontent.com/ImperialCollegeLondon/covi...</pre>


