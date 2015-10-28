=============================
 Dealing with Launchpad bugs
=============================

Usage
-----

lpgrabber downloads Launchpad project information in csv format suitable for data analysis with pandas.

Usage:

  lpgrabber --help

  lpgrabber [--milestone X.X] [--updated-since YYYY-MM-DD] [--open-only] [--update-csv previous.csv] bugs project_name

  lpgrabber teams search_string

  lpgrabber gerrit [—branch branch] [—open-only] search_string


TODO
----

- add some speed by running requests in parallel
- for milestone we need two filters: one for main bugtasks and one for tasks on particular series
- basic usage instruction
- unit tests with mocks for main cases
- report script with pandas for Fuel
- implement --reviews-list and --history flags for bugs
- implement gerrit integration
