# RAS 2026 Competition Datasets — File Reference

**Version:** v3 (June 2026)  
**Spec:** Problem Statement (`docs/problem_statement.pdf`) §3 (Input Data Format)


This document defines every file and field shipped under
`datasets/{l1,l2,l3}/`. The core solver-input files use the same schema
across all three network-resolution layers; only the demand population
differs. The informational `yard_car_demand_summary.csv` file may include
additional commodity-specific summary columns.

---

## 1. Layer summary

All three layers share identical `node.csv` files (47,193 nodes).
L1 and L2 also ship identical `link.csv` files; L3 uses the same link
IDs/schema with minor track-value fill and length-rounding differences.
The demand populations differ by layer.

| Layer | Origins | Destinations | OD pairs | Demand rows | Total volume (cars) |
|---|---:|---:|---:|---:|---:|
| **L1** | 21 | 21 | 411 | 775 | 541,860 |
| **L2** | 74 | 132 | 1,618 | 2,044 | 3,123,123 |
| **L3** | 80 | 414 | 1,998 | 2,427 | 3,132,664 |

L1 = super-hump skeleton; L2 = + major flat yards; L3 = current largest
released demand snapshot with yard_level 1/2/3 demand coverage.

> **Archived-file note (v2.1 archive).** The table above records the
> layer *design* targets. Statistics computed directly from the archived
> `demand.csv` files are reported in the repository `README.md`
> ("Observed statistics of the archived v2.1 files"). In the archived
> v2.1 package the L1 `demand.csv` has the same demand population as L2
> (2,044 rows, 74 origins, 132 destinations, 3,123,123 cars).
See spec §5.6 for the complete L1/L2/L3 + ×0.5/×1.0/×2.0 scenario matrix.

---

## 2. node.csv — physical network nodes

One row per node. Includes yards (classification facilities), stations
(intermediate junctions on the physical track network), and connector
nodes used by the route-graph topology.

| Field | Type | Unit | Description |
|---|---|---|---|
| `node_id` | int | — | Unique node identifier (sequential). |
| `node_type` | string | — | One of `yard`, `station`, `micro`, `gate`. Only `yard` rows participate as demand endpoints and as classification points. |
| `x_coord` | float | decimal degrees (WGS84) | Longitude. |
| `y_coord` | float | decimal degrees (WGS84) | Latitude. |
| `name` | string | — | Display name (e.g., `AUBURN`, `MEMPHIS`). Empty for non-yard nodes. |
| `yard_type` | string | — | For yards only: `hump`, `major_flat`, `intermodal`, or `local`. See remarks below. |
| `yard_level` | int (1-3) | — | Yard-size hierarchy: 1 = Class I super-humps (21 yards), 2 = major-flat regional (111), 3 = local (1,345). |
| `railroad_id` | string | — | Owning railroad: `UP`, `BNSF`, `CSX`, `NS`, `CN`, `CPKC`, or a placeholder for non-yard nodes. |
| `num_tracks` | float | classification tracks | Maximum number of outbound classification (Manifest/Bulk) blocks the yard can build per operating cycle. **Per v1.5 §2.2 C2: counted only for Manifest/Bulk blocks; intermodal/multilevel blocks bypass this budget.** |
| `handling_capacity` | float | cars / 70-day cycle | Maximum cars classified at this yard per operating cycle. Applies to inbound flow at intermediate yards in a multi-block sequence (see spec C3). Pass-through traffic does not count. |
| `handling_cost` | float | $ / car | Per-car classification handling cost at this yard. Used by C3 cost calculation. |
| `is_interchange` | bool | — | TRUE if the yard is a designated multi-railroad interchange point. |
| `allowed_commodities` | string | — | Comma-separated list of commodities the yard can classify (e.g., `merchandise,coal,grain`). Advisory; the operative restriction is in spec §1.1 / C2. |
| `allowed_traversal` | string | — | Always `all` in this release; reserved for future per-mode restrictions. |
| `datasource` | string | — | Provenance note (e.g., `Estimated based on yard level`, `Satellite imagery — manual estimate`). |

### Yard-level remarks

- **Level 1 (super-humps)**: 21 nodes. Each represents a multi-modal Class I yard *complex* — hump bowl, intermodal ramp, and auto facility co-located. The `num_tracks` field reflects hump-bowl tracks only.
- **Level 2 (major flat)**: 111 nodes. Regional flat-classification yards.
- **Level 3 (local)**: 1,345 nodes. Smaller industry-serving yards, intermodal sub-terminals, and regional connectors.
- Nodes with `node_type ≠ yard` carry placeholder values (0 / blank) for yard-only fields.

### Capacity defaults table (cross-reference)

| `yard_level` | `handling_capacity` (cars / 70-day) | typical `num_tracks` |
|---|---:|---:|
| 1 | 30,000 | 20-70 |
| 2 | 5,000-10,000 | 5-30 |
| 3 | 1,500-3,000 | 3-10 |

These are the curated defaults; concrete per-yard values are in
`node.csv`. See spec §3.4 *Parameter provenance*.

---

## 3. link.csv — physical track segments

One row per directed track segment.

| Field | Type | Unit | Description |
|---|---|---|---|
| `link_id` | int | — | Unique link identifier (sequential). |
| `from_node_id` | int | — | Origin node. References `node_id` in `node.csv`. |
| `to_node_id` | int | — | Destination node. |
| `length` | float | miles | Physical length of the segment. Used in transport-cost calculation and shortest-path distance. |
| `capacity` | float | cars / 70-day cycle | Link throughput capacity (C5). |
| `railroad_id` | string | — | Owning railroad. `-1` for shared / connector links. |
| `free_speed` | float | mph | Reference operating speed. Not used in the v1.5 objective; reserved for future scheduling extensions. |
| `tracks` | float | physical tracks | Number of parallel main tracks on this segment. Informational; capacity already reflects multi-track effects. |
| `geometry` | string | WKT LINESTRING | Lon/lat polyline geometry for visualization. Optional for solver input. |

### Link remarks

- **Capacity convention**: physical mainline links are assigned 700,000 cars / 70-day; connector links 10,000. These are calibrated 70-day-cycle figures consistent with double-tracked Class I corridors at ~30-40 trains/day × ~150 cars/train. See spec §3.4 *Parameter provenance*.
- Links are **directed**. A bidirectional physical track is represented by two link rows (one per direction).

---

## 4. demand.csv — yard-to-yard commodity demand

One row per (commodity, OD pair). All volumes are over the **full 70-day operating cycle**.

| Field | Type | Unit | Description |
|---|---|---|---|
| `demand_id` | int | — | Unique commodity row identifier. |
| `origin_yard_id` | int | — | Origin yard node_id. Must reference a `node_type=yard` node. |
| `dest_yard_id` | int | — | Destination yard node_id. Must reference a `node_type=yard` node. |
| `volume` | int | railcars / 70-day | Demand volume in car-equivalent units over the operating cycle. |
| `block_type` | string | — | Commodity-derived block type. One of `Merchandise`, `Intermodal`, `Coal`, `Grain`, `Automobile`. |

### Commodity / block_type mapping (per spec §1.1)

| `block_type` value | Commodity | Block category | Direct-only? |
|---|---|---|---|
| `Merchandise` | Merchandise (mixed manifest cars) | Manifest | No (hub-and-spoke OK) |
| `Coal` | Coal (unit train or manifest) | Bulk / Manifest | No |
| `Grain` | Grain (unit train or manifest) | Bulk / Manifest | No |
| `Intermodal` | Intermodal (containers / trailers) | Intermodal | **Yes** — single-block, no intermediate humping |
| `Automobile` | Automobile (multilevel) | Multilevel | **Yes** — single-block, no intermediate humping |

### Demand remarks

- Volumes are **integer** railcars at the 70-day basis; divide by 70 for daily, or by 10 for weekly. See spec §3.3.
- All ODs are yard-to-yard. Zone-to-yard mapping has already been performed in dataset prep.
- Block_type is determined by the commodity and shapes which rules apply (hump-yard restrictions, direct-only sequencing, etc.).

---

## 5. setting.csv — global parameters

One row per parameter. CSV columns: `parameter, value, unit, description`.

| Parameter | Default | Unit | Description |
|---|---:|---|---|
| `min_block_vol_short(<100mi)` | 350 | railcars | Min volume for blocks under 100 miles (C4) |
| `min_block_vol_med(100-500mi)` | 700 | railcars | Min volume for blocks 100-500 miles (C4) |
| `min_block_vol_long(>500mi)` | 1050 | railcars | Min volume for blocks over 500 miles (C4) |
| `max_circuitous_ratio` | 1.3 | ratio | Max detour factor vs. shortest path (C6) |
| `operating_cycle` | 70 | days | Planning horizon |
| `block_fixed_cost` | 2500 | $/block | Fixed cost per opened block |
| `transport_cost_coefficient` | 1 | $/car-mile | Per car-mile transportation cost coefficient |
| `interchange_cost` | 100 | $/car | Per-car cost penalty for railroad interchange traffic |
| `stress_penalty_M` | 5 | $/car-mile | v1.5 §6.4 Stress Score penalty coefficient (range [5, 10]) |
| **`demand_multiplier`** | **1.0** | ratio | **v1.5 §3.4 demand-volume multiplier; set to 0.5 or 2.0 for the corresponding scenario sub-case (spec §5.6)** |

### Demand scaling (spec §5.6)

Per spec §5.6, the three official scenario sub-cases are ×0.5, ×1.0,
and ×2.0. They all use the same `demand.csv`; the multiplier is the
sole difference. To run a sub-case, change the `value` of the
`demand_multiplier` row in `setting.csv` (or override at runtime).

The solver MUST echo the chosen multiplier into
`inputs.settings.demand_multiplier` of the submission's
`solution_result.json`. The released validation logic under `../scoring/`
reads this field and multiplies demand volumes by it *before* any constraint
check or cost calculation. If the field is absent, the validation logic
assumes 1.0.

---

## 6. yard_car_demand_summary.csv — per-yard demand summary (informational)

Convenience summary. Not required as solver input, and not guaranteed to
be a strict aggregation of the current `demand.csv`.

| Field | Type | Unit | Description |
|---|---|---|---|
| `yard_id` | int | — | Yard node_id. |
| `yard_name` | string | — | Display name. |
| `yard_level` | int (1-3) | — | Same as in `node.csv`. |
| `yard_type` | string | — | Same as in `node.csv`. |
| `handling_capacity` | float | cars / 70-day | Same as in `node.csv`. |
| `sent_demand` | int | cars / 70-day | Informational sent-demand estimate for this yard; not guaranteed to equal the strict sum of current `demand.csv` rows. |
| `received_demand` | int | cars / 70-day | Informational received-demand estimate for this yard; not guaranteed to equal the strict sum of current `demand.csv` rows. |
| `usage` | float (0-1) | — | Capacity utilization estimate based on the summary fields (`max(sent_demand, received_demand) / handling_capacity`). Informational. |
| `sent_demand_<BlockType>` | number | cars / 70-day | Optional commodity-specific sent-demand summary column. Present in some layers. |
| `received_demand_<BlockType>` | number | cars / 70-day | Optional commodity-specific received-demand summary column. Present in some layers. |

Useful for high-level sanity-checking of yard demand pressure before the
solver runs. Feasibility checks should use `demand.csv`, `node.csv`, and
the scoring validator.

---

## 7. Provenance, units, and limitations

See spec §5.5 *Data Provenance and Limitation Note*. Brief summary:

- **Demand**: derived from BTS/FAF freight-flow data; transformed into
  yard-to-yard car-equivalents through aggregation, mapping, scaling,
  and benchmark calibration. **Not a re-publication of any official
  BTS or FAF dataset.**
- **Network**: research-derived. Spatial connectivity was developed in
  part from OpenStreetMap (OSM) data (© OpenStreetMap contributors,
  ODbL 1.0), followed by processing, filtering, simplification, and
  research curation by the RAS Class I industry partners and the
  problem-development team. **Not a direct OSM extract.**
- **Parameters** (capacity, costs): provisional defaults for algorithmic
  evaluation. The transport_cost_coefficient is set to 1 to balance
  transport vs. handling cost in the resulting plan.
- **No warranty.** See spec §5.5 in full.

When using this benchmark in publications, please cite:

> Peiheng Li and Xuesong (Simon) Zhou. *INFORMS RAS 2026 Problem Solving Competition*. Kaggle, 2026.
> https://www.kaggle.com/competitions/informs-ras-2026-problem-solving-competition

Users relying on upstream public source datasets should additionally cite
the applicable original sources, including FAF and OpenStreetMap, as
appropriate. When discussing the underlying lineage, please use phrasing
such as "derived from BTS/FAF freight-flow data" and "research-derived in
part from OpenStreetMap data"; do not describe the benchmark as a direct
BTS, FAF, or OSM extract. The full notice is in
[`../DATA_PROVENANCE_AND_USE.md`](../DATA_PROVENANCE_AND_USE.md).

---

## 8. Quick consistency checks

Before running a solver, sanity-check:

- Every `origin_yard_id` and `dest_yard_id` in `demand.csv` exists in
  `node.csv` with `node_type = 'yard'`.
- For each yard, `sent_demand + received_demand` is broadly consistent
  with `handling_capacity`. Where `sent_demand > handling_capacity`,
  some demand will be unservable under strict feasibility (this is by
  design at L3 ×2.0 — see spec §5.6 stress scenario).
- `link.csv` connectivity covers the union of all (origin, destination)
  yard pairs in `demand.csv` — i.e., a path exists for every OD.

For released feasibility checks and scoring behavior, refer to the validation
logic documented under `../scoring/`. It checks feasibility (spec C1-C7) and
emits Loaded Demand Ratio + Stress Score (spec §6.4).
