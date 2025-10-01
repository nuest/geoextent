

add support for a single ZIP file in a remote repository, test with the Zenodo content provider and
  https://doi.org/10.5281/zenodo.3446746




fix building of the documentation in CI and add documentation to the README on building the documentation locally with the latest version of Sphinx; update the documentation to include all relevant documentation
  and information from the README and subsequently make a suggestion on which content to retain in the README to reduce the README's size; the documentation should focus on a handful of example remote URLs based on
  the README that include data less than 100MB for fast execution but at the same time covers all features (content providers, data file formats)


fix the issue in the Dockerfile that pandas requires version 1.3.6 of bottleneck but 1.3.5 is install; fix that the --quiet flag should also suppress INFO level messages from the underlying libraries like patool, e.g.,

eoextent -b --max-download-size 10MB --quiet https://doi.org/10.5281/zenodo.10731546
/usr/local/lib/python3.12/dist-packages/pandas/core/arrays/masked.py:61: UserWarning: Pandas requires version '1.3.6' or newer of 'bottleneck' (version '1.3.5' currently installed).
  from pandas.core import (
INFO patool: could not find a 'file' executable, falling back to guess mime type by file extension
INFO:patool:could not find a 'file' executable, falling back to guess mime type by file extension
INFO patool: could not find a 'file' executable, falling back to guess mime type by file extension
INFO:patool:could not find a 'file' executable, falling back to guess mime type by file extension
INFO patool: could not find a 'file' executable, falling back to guess mime type by file extension
INFO:patool:could not find a 'file' executable, falling back to guess mime type by file extension
{"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[0.341496825115861, 0.3414558847200173], [52.075344297417736, 0.3414558847200173], [52.075344297417736, 52.0751897250789], [0.341496825115861, 52.0751897250789], [0.341496825115861, 0.3414558847200173]]]}, "properties": {"format": "remote", "crs": "4326", "extent_type": "bounding_box", "description": "Bounding box extracted by geoextent"}}]}
