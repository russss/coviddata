import xarray as xr


def merge(*datasets):
    output = xr.merge(datasets, compat="override")
    for attr in ["source", "source_url", "date"]:
        output.attrs[attr] = [ds.attrs[attr] for ds in datasets]

    return output
