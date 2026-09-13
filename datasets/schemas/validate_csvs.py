"""validate_csvs.py — Validate all RAS 2026 CSVs against their JSON schemas.

Usage:
    python validate_csvs.py [--datasets-dir <path>] [--strict]

Requires:
    pip install jsonschema

Walks datasets/{l1,l2,l3}/ and validates every CSV against the matching
schema in this folder. Reports the first error per file (or all errors
in --strict mode). Exits 0 if all rows validate, 1 otherwise.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    sys.stderr.write("ERROR: pip install jsonschema\n")
    sys.exit(2)

SCHEMA_DIR = Path(__file__).resolve().parent

def _f0(v):
    return float(v) if str(v).strip() else 0.0
def _bool(v):
    return str(v).strip().lower() in ("true", "1", "yes")

# Per-CSV column casting rules
NODE_CAST = {
    "node_id": int, "yard_level": _f0,
    "x_coord": float, "y_coord": float, "num_tracks": _f0,
    "handling_capacity": _f0, "handling_cost": _f0,
    "is_interchange": _bool,
}
LINK_CAST = {
    "link_id": int, "from_node_id": int, "to_node_id": int,
    "length": float, "capacity": float, "free_speed": float, "tracks": float,
}
DEMAND_CAST = {
    "demand_id": int, "origin_yard_id": int, "dest_yard_id": int, "volume": float,
}
SUMMARY_CAST = {
    "yard_id": int, "yard_level": float,
    "handling_capacity": float, "sent_demand": float, "received_demand": float,
    "usage": float,
}

SETTING_CAST = {"value": float}

CSV_SPECS = [
    ("node.csv",                      "node.schema.json",                      NODE_CAST),
    ("link.csv",                      "link.schema.json",                      LINK_CAST),
    ("demand.csv",                    "demand.schema.json",                    DEMAND_CAST),
    ("setting.csv",                   "setting.schema.json",                   SETTING_CAST),
    ("yard_car_demand_summary.csv",   "yard_car_demand_summary.schema.json",   SUMMARY_CAST),
]
SCALED_DEMAND_FILES = []   # v1.5: scaled_demand/ folder retired in favor of demand_multiplier in setting.csv


def cast_row(row: dict, casters: dict) -> dict:
    """Cast typed columns. Drop empty cells so JSON-Schema validates
    only fields that are actually present in this row (required-field
    enforcement still catches truly missing required columns)."""
    out = {}
    for k, v in row.items():
        if v is None or v == "":
            continue   # drop empty cell from the row dict
        cast = casters.get(k, str)
        try:
            out[k] = cast(v)
        except (ValueError, TypeError):
            out[k] = v
    return out


def validate_csv(csv_path: Path, schema: dict, casters: dict, strict: bool) -> tuple[int, int]:
    validator = jsonschema.Draft202012Validator(schema)
    n_rows = 0
    n_errors = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        for i, raw in enumerate(csv.DictReader(f), start=1):
            n_rows += 1
            row = cast_row(raw, casters)
            errs = list(validator.iter_errors(row))
            if errs:
                n_errors += 1
                if strict or n_errors == 1:
                    msg = errs[0].message
                    print(f"  [row {i}]  {msg}")
                if not strict:
                    break
    return n_rows, n_errors


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--datasets-dir", default=str(SCHEMA_DIR.parent),
                   help="Path to the datasets/ folder (default: parent of this script)")
    p.add_argument("--strict", action="store_true",
                   help="Report ALL errors per file, not just the first")
    args = p.parse_args()

    ds_root = Path(args.datasets_dir).resolve()
    print(f"Validating CSVs under {ds_root}\n")

    schemas = {}
    for _, name, _ in CSV_SPECS:
        schemas[name] = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    schemas["demand.schema.json"]  # ensure loaded for scaled_demand

    total_files = 0
    total_errors = 0

    for layer in ("l1", "l2", "l3"):
        layer_dir = ds_root / layer
        if not layer_dir.is_dir():
            continue
        print(f"=== {layer.upper()} ===")
        for csv_name, schema_name, casters in CSV_SPECS:
            csv_path = layer_dir / csv_name
            if not csv_path.exists():
                continue
            total_files += 1
            n_rows, n_errors = validate_csv(csv_path, schemas[schema_name],
                                             casters, args.strict)
            tag = "PASS" if n_errors == 0 else "FAIL"
            print(f"  [{tag}]  {csv_name:<35} {n_rows:>8,} rows  {n_errors} errors")
            total_errors += n_errors
        # Scaled demand files share demand.schema.json
        for sd_rel in SCALED_DEMAND_FILES:
            sd_path = layer_dir / sd_rel
            if not sd_path.exists():
                continue
            total_files += 1
            n_rows, n_errors = validate_csv(sd_path, schemas["demand.schema.json"],
                                             DEMAND_CAST, args.strict)
            tag = "PASS" if n_errors == 0 else "FAIL"
            print(f"  [{tag}]  {sd_rel:<55} {n_rows:>8,} rows  {n_errors} errors")
            total_errors += n_errors
        print()

    print(f"Validated {total_files} CSV files. Total errors: {total_errors}.")
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
