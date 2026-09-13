# L2 — Major-Flat-Yard Tier

**Layer:** Network resolution L2 (super-humps + major flat yards)
**Origins / Dests:** 74 / 132
**OD pairs:** 1,618
**Demand rows:** 2,044
**Total volume (×1.0 baseline):** 3,123,123 cars / 70-day cycle

---

## What's in this folder

| File | Purpose |
|---|---|
| `node.csv` | Physical network nodes (47,193 rows; 1,477 yards). Identical to L1 and L3. |
| `link.csv.zip` | Physical track segments (unzip to `link.csv`) (106,570 rows). Identical to L1; L3 uses the same link IDs/schema but differs in track values and minor length rounding. |
| `demand.csv` | Yard-to-yard commodity demand for L2 (2,044 rows). **L2-specific.** ×1.0 baseline; sub-cases via `demand_multiplier`. |
| `setting.csv` | v1.5 global parameters; default `demand_multiplier = 1.0`. |
| `yard_car_demand_summary.csv` | Per-yard demand summary (informational; not a strict aggregation of the current `demand.csv`). |

For field-level definitions of every column in every file, see
[`../DATASET_README.md`](../DATASET_README.md). For the demand-scaling
workflow (×0.5, ×1.0, ×2.0 sub-cases), see the L1 README — same
mechanism applies here.

---

## L2-specific remarks

- Demand spans yard_level 1 and 2 yards: 74 origin yards and 132
  destination yards in the current `demand.csv`.
- Block_type mix in baseline `demand.csv`:
  - Merchandise: 1,519 rows
  - Intermodal: 327 rows
  - Grain: 110 rows
  - Automobile: 87 rows
  - Coal: 1 row
- Hub-and-spoke routing through the 21 super-humps becomes meaningful
  here.
