# L3 — Full National Benchmark

**Layer:** Network resolution L3 (full national curated benchmark)
**Origins / Dests:** 80 / 414
**OD pairs:** 1,998
**Demand rows:** 2,427
**Total volume (×1.0 baseline):** 3,132,664 cars / 70-day cycle

---

## What's in this folder

| File | Purpose                                                                                                                 | Size |
|---|-------------------------------------------------------------------------------------------------------------------------|---:|
| `node.csv` | Physical network nodes (47,193 rows; 1,477 yards). Identical to L1 and L2. | ~2.4 MB |
| `link.csv.zip` | Physical track segments (unzip to `link.csv`) (106,570 rows). Same link IDs/schema as L1 and L2, with filled track values and minor length rounding differences. | ~72.6 MB |
| `demand.csv` | Yard-to-yard commodity demand for L3 (2,427 rows). **L3-specific.** ×1.0 baseline; sub-cases via `demand_multiplier`. | ~0.08 MB |
| `setting.csv` | v1.5 global parameters; default `demand_multiplier = 1.0`.                                                              | <1 KB |
| `yard_car_demand_summary.csv` | Per-yard demand summary (informational; not a strict aggregation of the current `demand.csv`).                         | ~0.09 MB |

For field-level definitions of every column in every file, see
[`../DATASET_README.md`](../DATASET_README.md).

---

## L3-specific remarks

- Demand spans yard_level 1, 2, and 3 yards: 80 origin yards and 414
  destination yards in the current `demand.csv`. All five commodity
  types are present (intermodal, merchandise, coal, grain, automobile).
- Block_type mix in baseline `demand.csv`:
  - Merchandise: 1,902 rows
  - Intermodal: 327 rows
  - Grain: 110 rows
  - Automobile: 87 rows
  - Coal: 1 row
- This is the largest released demand file among L1/L2/L3 in the current
  CSV snapshot, with broader destination coverage than L2.

---

## Performance expectations (reference)

No reference runtime is stated for this CSV snapshot. Runtime and output
JSON size should be measured against the current `demand.csv` rather than
older full-national benchmark notes.

---

## Running the three demand-scaling sub-cases

Identical workflow to L1 / L2: edit `demand_multiplier` in
`setting.csv` (or override at runtime) and re-run your solver. The
validators read the chosen multiplier from
`inputs.settings.demand_multiplier` in your `solution_result.json` and
apply it before computing all metrics.
