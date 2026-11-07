# Filter curves

`neutral_print_filters.json` is calibration data written for this runtime. It stays in the tree.

The dichroic, Schott heat-absorbing, and Canon lens CSVs are not included. A redistribution license for those curves was not established. See the repository `LICENSING.md`.

To use a curve you are allowed to read, set `SPEKTRAFILM_FILTER_DIR` to a directory with the same relative paths the loader expects, for example `heat_absorbing/schott/KG3.csv`. The process does not download curves.

Default negative prints ask for enlarger illuminant `TH-KG3`, which reads that Schott KG3 file. The default enlarger dichroic is the analytic `custom` model and does not read the Thorlabs, Edmund, or Durst CSVs. `TH-KG3-L` additionally reads `lens_transmission/canon/canon_24_f28_is.csv`.
