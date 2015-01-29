JSON specification
==================

`$foo` are custom ids that are not exposed to a user but may be used as HTML ids
(restrictions to white-space and special characters eg. `.` or `#`
apply and they must be globally unique).
`<"foo">` are optional fields in an object.
Colors are all valid CSS colors (named, hexadecimal, rgb, …)
A set of good colors is `["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494", "#b3b3b3"]`.
Timestamps are UNIX timestamps in seconds since standard epoch.

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
  ]
  "events": [ // a list of events
    {
      "group": $group_id,
      "id": $type_id,
      "time": 1288756800, // timestamp
      <"flag">: $flag_id, // optional event flag
      <"flag_value">: "4mg", // optional event flag display value
      <"event_id">: $event_id, // optional id for this event
      <"connections">: [ // directed connections to other events (the direction is ignored for now)
        $event_id, // the event id of the connected event
        …
      ],
      <"weight">: 0.75 // an associated weight to the event (shown as circle)
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
