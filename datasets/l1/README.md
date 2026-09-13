# L1 — Super-Hump Skeleton

**Layer:** Network resolution L1 (Class I super-hump skeleton)
**Origins / Dests:** 21 / 21
**OD pairs:** 411
**Demand rows:** 775
**Total volume (×1.0 baseline):** 541,860 cars / 70-day cycle

> **Archived-file note.** The figures above are the L1 layer design
> targets. The `demand.csv` archived in this v2.1 package contains
> 2,044 rows (74 origins, 132 destinations, 1,618 OD pairs,
> 3,123,123 cars), the same demand population as L2. See the
> repository `README.md` for statistics computed from the archived files.

---

## What's in this folder

| File | Purpose |
|---|---|
| `node.csv` | Physical network nodes (47,193 rows; 1,477 yards). Identical to L2 and L3. |
| `link.csv.zip` | Physical track segments (unzip to `link.csv`) (106,570 rows). Identical to L2; L3 uses the same link IDs/schema but differs in track values and minor length rounding. |
| `demand.csv` | Yard-to-yard commodity demand for L1 (775 rows). **L1-specific.** Ships at the ×1.0 baseline; sub-cases are produced at runtime by changing `demand_multiplier` in setting.csv (see spec §3.4 / §5.6). |
| `setting.csv` | All v1.5 global parameters (block_fixed_cost, transport_cost_coefficient, demand_multiplier, etc.). Default `demand_multiplier = 1.0`. |
| `yard_car_demand_summary.csv` | Per-yard demand summary (informational; not a strict aggregation of the current `demand.csv`). |

For field-level definitions of every column in every file, see
[`../DATASET_README.md`](../DATASET_README.md).

---

## Running the three demand-scaling sub-cases

Per spec §5.6 the official sub-cases are ×0.5, ×1.0, ×2.0. To run a
sub-case, edit the `value` field of the `demand_multiplier` row in
`setting.csv` (or override at runtime) and re-run your solver. The
released validation logic under `../../scoring/` reads the multiplier from
`inputs.settings.demand_multiplier` in your `solution_result.json` and
applies it before computing constraint checks and metrics.

```bash
# ×0.5 sub-case: edit setting.csv → demand_multiplier = 0.5, then
your_solver --node node.csv --link link.csv --demand demand.csv \
            --settings setting.csv --output solution_x0p5.json
```

For validation and scoring commands, refer to `../../scoring/SCORE_README.md`.

The same `demand.csv` is used for all three multiplier values; the
multiplier is the only difference between sub-cases.

---

## L1-specific remarks

- Demand is restricted to the **21 Class I super-hump complexes** (yard_level = 1).
- Block_type mix in baseline `demand.csv`:
  - Intermodal: 389 rows
  - Grain: 360 rows
  - Merchandise: 11 rows
  - Automobile: 8 rows
  - Coal: 7 rows
- Suitable as a **rapid-prototyping** instance — the small OD count
  keeps even slow methods tractable, while the full physical network
  and the five-commodity mix exercise all v1.5 constraints.
