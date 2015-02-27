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

## Patient file creation format

TODO text and comments

```javascript
{
  "patient_id": 'DESYNPUF_ID',
  <"born">: 'BENE_BIRTH_DT',
  <"death">: 'BENE_DEATH_DT',
  <"gender">: 'BENE_SEX_IDENT_CD',
  <"claim_amount">: 'CLM_PMT_AMT',
  <"claim_from">: 'CLM_FROM_DT',
  <"claim_to">: 'CLM_THRU_DT',
  "diagnosis": [
    'ICD9_DGNS_CD_1',
    'ICD9_DGNS_CD_2',
    …
  ],
  "procedures": [
    'ICD9_PRCDR_CD_1',
    'ICD9_PRCDR_CD_2',
    …
  ],
  <"prescribed_date">: 'SRVC_DT',
  <"prescribed">: 'PROD_SRVC_ID',
  <"prescribed_amount">: 'PTNT_PAY_AMT',
  <"lab_date">: 'LAB_RSL_SERVICE_DATE',
  <"lab_code">: 'LOINC',
  <"lab_result">: 'LAB_RSL',
  <"lab_flag">: 'LAB_NORMAL'
}
```

## Web input format

TODO text

The specification is split into two files, the dictionary containing all types (ie. rows)
and the events containing all events (ie. boxes).

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
      }
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
  <"v_bars">: [ // to highlight special times
    "auto" // auto detect interesting times —- otherwise a list of timestamps
  ],
  <"total">: [ // shows a continuous line chart below the event display
    [ 1306757400, 0.75 ], // pairs of timestamps and values
    …
  ]
}
```
