# Feature Extraction

A binary feature matrix can be extracted using the `extract.py` script.
The output is a CSV table with columns `id` and named after the event types:
`${group_id}__${type_id}` where `${group_id}` and `${type_id}` are as defined
[in the specification](../spec.md).
The script needs to be run from this folder.

```bash
./extract.py -w cohort.txt --age-time 20100101 --to 20100101 -o output.csv -f ../format.json -c ../config.txt -- ../opd
```

Be aware that the run time is approximately ~1h.

TODO Currently medication is ignored -> needs a command line way to specify age bin size and ignored groups

For more information about arguments call `./extract.py -h`.
You can use `./build_dictionary.py -c config.txt --lookup ${column_name...}`
to look up proper names for the columns.
