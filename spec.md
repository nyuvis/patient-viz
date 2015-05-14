# Importing own data

TODO text

## How to read the specifications

The input formats described in this document are JSON files.
`$foo` are custom ids that are not exposed to a user but may be used as HTML ids
(restrictions to white-space and special characters eg. `.` or `#`
apply and they must be globally unique).
`<"foo">` are optional fields in an object.
Colors are all valid CSS colors (named, hexadecimal, rgb, …)
A set of good colors is `["#80b1d3", "#4daf4a", "#fb8072", "#ff7f00", "#eb9adb"]`.
Timestamps are UNIX timestamps in seconds since standard epoch.
Keep in mind that the unit for positions is determined by the smallest difference
between events. It might be better to bin timestamps into coarser steps when
the input times are too granular (the visualization might become flat or invisible).
Binning also helps to make co-occurring events behave more intuitive.

## Patient file creation format

TODO text and comments
TODO arrays for first match

```javascript
{
  "patient_id": "DESYNPUF_ID",
  <"age">: "ELIG_AGE",
  <"born">: "BENE_BIRTH_DT",
  <"death">: "BENE_DEATH_DT",
  <"gender">: "BENE_SEX_IDENT_CD",
  "provider_ibc": [
  ],
  "provider_cms": [
    "PRVDR_NUM"
  ],
  "physician_ibc": [
  ],
  "physician_cms": [
    "AT_PHYSN_NPI",
    …
  ],
  <"claim_id">: "CLM_ID",
  <"claim_amount">: "CLM_PMT_AMT",
  <"claim_from">: "CLM_FROM_DT",
  <"claim_to">: "CLM_THRU_DT",
  <"admission">: "CLM_ADMSN_DT",
  <"discharge">: "NCH_BENE_DSCHRG_DT",
  <"location_flag">: "ENCS_FACILITY_TYPE",
  "diagnosis_icd9": [
    "ICD9_DGNS_CD_1",
    "ICD9_DGNS_CD_2",
    …
  ],
  "procedures_icd9": [
    "ICD9_PRCDR_CD_1",
    "ICD9_PRCDR_CD_2",
    …
  ],
  "procedures_cpt": [
    "ENCS_CPTCODE",
    …
  ],
  "procedures_hcpcs": [
    "HCPCS_CD_1",
    "HCPCS_CD_2",
    …
  ],
  <"prescribed_date">: "SRVC_DT",
  <"prescribed">: "PROD_SRVC_ID",
  <"prescribed_amount">: "PTNT_PAY_AMT",
  <"lab_date">: "LAB_RSL_SERVICE_DATE",
  <"lab_code">: "LOINC",
  <"lab_result">: "LAB_RSL",
  <"lab_flag">: "LAB_NORMAL"
}
```

You can update converted patient files using `./start.sh --refresh`.
An initial `./setup.sh --burst` is recommended in doing so since it speeds up patient file conversion.

## Web input format

TODO text

The specification is split into two files, the dictionary containing all types (ie. rows)
and the events containing all events (ie. boxes).

Type ids (`$type_id`) can also consist of a prefixed version of a code (eg.
`250.00`, `icd9__250.00`, `25000`, or `icd9__25000` are all representations
of the `diagnosis` (`$group_id`) with the description:
"Diabetes mellitus without mention of complication").

The dictionary file:

```javascript
{
  $group_id: { // the group id
    $type_id: { // the type id
      "id": $type_id, // the same as type id
      "parent": $parent_id, // a parent type in the same group or "" for the root
      "name": "Lenalidomide", // the short name of the type
      "desc": "Lenalidomide [100 CAPSULE in 1 BOTTLE (59572-410-00)] (Revlimid) - Thalidomide Analog [EPC] - HUMAN PRESCRIPTION DRUG", // a longer description
      <"color">: "#aabbcc", // the color of this type -- if not present the parents color will be used (or automatically assigned if no color is specified)
      <"flags">: {
        $flag_id: {
          "color": "#bbccdd" // the color to use when the flag $flag_id is specified
        },
        …
      },
      <"unmapped">: false, // marker for types that are not in the dictionary and just have
                           // the id as name -- when creating your own dictionary this field should be missing or at least be false
      <"alias">: $type_id // an optional alias for this type -- if the alias type is present it replaces the type description
    },
    …
  },
  …
}
```

The events file:

```javascript
{
  "start": 1288756800, // earliest timestamp (for range checks)
  "end": 1338177600, // last timestamp (for range checks)
  "info": [ // infos displayed at the top of the screen
    {
      "id": $info_id, // the id of the info field
      "name": "Gender", // the name of the info field
      "value": "M", // the value of the info field
      <"label">: "primary" // if present the value is displayed as bootstrap label with the specified class (eg. "label-primary")
    },
    …
  ],
  "events": [ // a list of events
    {
      "group": $group_id,
      "id": $type_id,
      "time": 1288756800, // timestamp
      <"row_id">: $row_id, // groups events of the same row together
      <"flag">: $flag_id, // optional event flag
      <"flag_value">: "4mg", // optional event flag display value
      <"event_id">: $event_id, // optional id for this event
      <"connections">: [ // directed connections to other events (the direction is ignored for now)
        {
          "event_id": $event_id, // the event id of the connected event
          <"color">: "#e78ac3", // the color of the connection or black
          <"stroke_width">: "1pt" // the thickness of the connection or 4px
        },
        …
      ],
      <"weight">: 0.75, // an associated weight to the event (shown as circle)
      <"cost">: 103.12 // associated cost
    },
    …
  ],
  <"h_bars">: [ // to highlight rows
    {
      "group": $group_id,
      "id": $type_id
    },
    …
  ],
  <"v_bars">: [ // to split the time line into segments
    "auto" // auto detect segments —- otherwise a list of timestamps
  ],
  <"v_spans">: [ // to highlight special time spans
    {
      "from": 1288756800, // timestamp
      <"to">: 1366503400, // the end of the span -- otherwise one unit of the granularity is used
      <"class">: $class_names // optional classes of the span, separated by space -- classes are defined below
    }
  ],
  <"classes">: {
    $class_name: { // the name of style classes separated by space
      $style: $value // style/value pairs that are valid for SVG rect
      …
    }
    …
  },
  <"total">: [ // shows a continuous line chart below the event display
    [ 1306757400, 0.75 ], // pairs of timestamps and values
    …
  ]
}
```

## Using shelve databases as input

Besides CSV files patient files can also be created using a shelve database.
For this the patient file creation pipeline looks like:

```bash
./shelve_access.py -p 3045033701 -c config.txt -o - | ./cms_get_patient.py -p 3045033701 -f format_shelve.json -o json/3045033701.json -- -
./build_dictionary.py -p json/3045033701.json -c config.txt -o json/dictionary.json
./start.sh --list-update
```

The list of ids can be obtained with `./shelve_access.py -c config.txt --list`.
