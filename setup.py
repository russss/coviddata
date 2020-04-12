import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="coviddata",
    version="0.0.1",
    author="Russ Garrett",
    author_email="russ@garrett.co.uk",
    description="COVID-19 data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
    install_requires=["xarray", "pandas", "requests", "lxml"],
)
