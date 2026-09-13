# JSON Schemas — RAS 2026 v1.5

Machine-readable [JSON Schema](https://json-schema.org/) (Draft 2020-12)
definitions of every CSV row schema and the solution_result.json output
structure. These complement the human-readable reference in
[`../DATASET_README.md`](../DATASET_README.md).

---

## Files

| File | Describes | Used to validate |
|---|---|---|
| `node.schema.json` | One row of `node.csv` | Each row of `datasets/{l1,l2,l3}/node.csv` |
| `link.schema.json` | One row of `link.csv` | Each row of `datasets/{l1,l2,l3}/link.csv` |
| `demand.schema.json` | One row of `demand.csv` | Each row of `datasets/{l1,l2,l3}/demand.csv` |
| `yard_car_demand_summary.schema.json` | One row of `yard_car_demand_summary.csv` | Per-yard summary rows |
| `solution_result.schema.json` | Top-level `solution_result.json` | The submission JSON the validators consume |

---

## Why JSON Schema for CSVs?

The CSV files are tabular, but each column has a defined type, range,
and (often) an enumerated set of allowed values. JSON Schema captures
all of that in one machine-readable file, and lets you validate by:

1. Reading the CSV into a list of dicts (one per row), and
2. Validating each dict against the row-schema.

This catches typos, out-of-range values, malformed enums, and missing
required columns before they cascade into solver failures.

---

## Custom annotations

The schemas use one custom keyword: **`x-unit`** — the physical unit of
the field (e.g., `cars / 70-day cycle`, `miles`, `$ / car`). This is
descriptive only; standard validators ignore it. We use it because
JSON Schema has no standard slot for units, and the units are part of
the spec contract.

---

## Quick validation example (Python, ~20 lines)

```python
import csv
import json
from pathlib import Path
import jsonschema

SCHEMA_DIR = Path("datasets/schemas")
schema = json.loads((SCHEMA_DIR / "demand.schema.json").read_text())
validator = jsonschema.Draft202012Validator(schema)

# Cast row strings to the types the schema expects
cast = {"demand_id": int, "origin_yard_id": int, "dest_yard_id": int,
        "volume": int, "block_type": str}

with open("datasets/l1/demand.csv", newline="") as f:
    for i, row in enumerate(csv.DictReader(f), start=1):
        typed_row = {k: cast.get(k, str)(v) for k, v in row.items()}
        errs = list(validator.iter_errors(typed_row))
        if errs:
            print(f"Row {i} failed: {errs[0].message}")
            break
    else:
        print("All rows valid.")
```

A reference implementation that validates **all four CSVs across all
three layers** is provided in [`validate_csvs.py`](validate_csvs.py).

---

## Casting CSVs to typed dicts

CSVs ship every column as a string. Before validating, you must cast:

| File | Integer cols | Float cols | Boolean cols | String cols |
|---|---|---|---|---|
| `node.csv` | `node_id`, `yard_level` | `x_coord`, `y_coord`, `num_tracks`, `handling_capacity`, `handling_cost` | `is_interchange` | `node_type`, `name`, `yard_type`, `railroad_id`, `allowed_commodities`, `allowed_traversal`, `datasource` |
| `link.csv` | `link_id`, `from_node_id`, `to_node_id` | `length`, `capacity`, `free_speed`, `tracks` | — | `railroad_id` (mixed int/string), `geometry` |
| `demand.csv` | `demand_id`, `origin_yard_id`, `dest_yard_id`, `volume` | — | — | `block_type` |
| `yard_car_demand_summary.csv` | `yard_id`, `yard_level`, `sent_demand`, `received_demand` | `handling_capacity`, `usage` | — | `yard_name`, `yard_type` |

(Boolean cells in CSV are stored as `True` / `False` strings; cast with
`{"True": True, "False": False}.get(v, v)`.)

---

Demand scaling variants are represented by the `demand_multiplier` row in
`setting.csv`; the retired `scaled_demand/` folder is not part of this
release.

## Spec cross-reference

| CSV / output | Spec section |
|---|---|
| `node.csv` | v1.5 §3.1 |
| `link.csv` | v1.5 §3.2 |
| `demand.csv` | v1.5 §3.3 + §5.6 |
| `yard_car_demand_summary.csv` | dataset convenience (no spec ref) |
| `solution_result.json` | v1.5 §4 |
