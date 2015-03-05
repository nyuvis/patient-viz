# Feature Extraction

A binary feature matrix can be extracted using the `extract.py` script.
The output is a CSV table with columns `id` and named after the event types:
`${group_id}__${type_id}` where `${group_id}` and `${type_id}` are as defined
[in the specification](../spec.md).

```bash
./extract.py -o output.csv -f ../format.json -c ../config.txt -- ../opd
```

