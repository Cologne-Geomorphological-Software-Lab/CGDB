# CGDB documentation

The Cologne Geomorphological Database System (CGDB) is a Django application for geoscientific research data, from field sampling to laboratory results. It is written for small research projects that have to meet the data management requirements of their funders but have no staff for data management.

CGDB records locations, layers and samples together with their laboratory analyses: luminescence, radiocarbon and cosmogenic nuclide dating, grain size, pollen counts, geochemistry and micro-XRF. It also keeps the instruments and methods used and the literature the data comes from. Access is granted per project and per role. The data can be edited in the admin, viewed on a map, queried through a REST API and exported to DuckDB for analysis.

To see it without installing anything but Docker, start with the [demo](getting-started/demo.md).

```{toctree}
:maxdepth: 2
:caption: Getting started

getting-started/demo
getting-started/installation
```

```{toctree}
:maxdepth: 2
:caption: Operations

operations/deployment
operations/roles-and-projects
operations/protected-files
operations/orchestration
```

```{toctree}
:maxdepth: 2
:caption: Development

development/testing
```

```{toctree}
:maxdepth: 2
:caption: Reference

reference/rest-api
reference/models
reference/changelog
reference/migrating
```

## Citing CGDB

> Handy, D. and van der Meij, M.: CGDB: Cologne Geomorphological Database System, Zenodo [code], https://doi.org/10.5281/zenodo.17869730, 2026.

> Handy, D., van der Meij, W. M., Zickel, M., and Reimann, T.: A database-driven research data framework for integrating and processing high-dimensional geoscientific data, Geosci. Instrum. Method. Data Syst., 15, 165–181, https://doi.org/10.5194/gi-15-165-2026, 2026.

Citation metadata for the current release are in [CITATION.cff](https://github.com/Cologne-Geomorphological-Software-Lab/CGDB/blob/main/CITATION.cff). CGDB is released under the MIT License.
