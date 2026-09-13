# INFORMS RAS 2026 Problem Solving Competition — Public Benchmark Archive

**Railroad Blocking Problem for North American Class I Railroads**

<p align="center"><img src="docs/header.png" alt="Overview map of the North American Class I railroad network used in the benchmark (illustrative)" width="560"></p>

This repository is the **ASU Trans+AI Lab research mirror and archival benchmark package** for the INFORMS Railway Applications Section (RAS) 2026 Problem Solving Competition: the railroad blocking benchmark instances, schemas, validators, scoring tools, documentation, and reproducibility resources (release v2.1). It does not replace the official competition pages linked below.

[![Kaggle](https://img.shields.io/badge/Kaggle-competition%20page-20BEFF?logo=kaggle&logoColor=white)](https://www.kaggle.com/competitions/informs-ras-2026-problem-solving-competition)
[![INFORMS RAS](https://img.shields.io/badge/INFORMS%20RAS-2026%20PSC-1F4E79)](https://connect.informs.org/railway-applications/new-item3/problem-solving-competition682)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-landing%20page-222222?logo=github)](https://asu-trans-ai-lab.github.io/RAS2026-PSC/)
[![Release](https://img.shields.io/github/v/release/asu-trans-ai-lab/RAS2026-PSC?label=release)](https://github.com/asu-trans-ai-lab/RAS2026-PSC/releases)
[![Code license: MIT](https://img.shields.io/badge/code%20license-MIT-green)](LICENSE-CODE)

---

## Official announcements

| Source | Link |
|---|---|
| **Kaggle — INFORMS RAS 2026 Problem Solving Competition** | https://www.kaggle.com/competitions/informs-ras-2026-problem-solving-competition |
| **INFORMS Railway Applications Section — 2026 Problem Solving Competition** | https://connect.informs.org/railway-applications/new-item3/problem-solving-competition682 |

> The Kaggle competition page is an authoritative source for the competition description, participation information, announcements, and competition materials.

> The INFORMS Railway Applications Section page is an authoritative source for the competition organization, leadership, timeline, and official RAS information.

---

## Citation

If you use this benchmark, please cite:

> Peiheng Li and Xuesong (Simon) Zhou. *INFORMS RAS 2026 Problem Solving Competition*. Kaggle, 2026.
> https://www.kaggle.com/competitions/informs-ras-2026-problem-solving-competition

```bibtex
@misc{li_zhou_ras2026,
  author       = {Li, Peiheng and Zhou, Xuesong (Simon)},
  title        = {INFORMS RAS 2026 Problem Solving Competition},
  year         = {2026},
  howpublished = {Kaggle},
  url          = {https://www.kaggle.com/competitions/informs-ras-2026-problem-solving-competition}
}
```

Users relying on upstream public source datasets should additionally cite the applicable original sources, including FAF and OpenStreetMap, as appropriate (see [Upstream source links](#upstream-source-links)). A machine-readable [`CITATION.cff`](CITATION.cff) is included.

---

## Problem summary

The competition targets the **static railroad blocking problem**: railcars are consolidated into blocks at classification yards and travel intact between yards. Participants construct a **zero-based blocking plan** from a physical rail network and a set of yard-to-yard commodity demands, with no pre-existing train or schedule information. The plan makes three simultaneous decisions: **block design** (which yard-to-yard blocks to open), **blocking sequence** (the single chain of blocks each commodity follows), and **block route** (the physical path each block takes on the network). Plans are evaluated on feasibility against constraints C1–C8 (flow conservation, classification-track limits, yard throughput, minimum block volume, link capacity, maximum circuity, single-path uniqueness, and commodity-type separation) and on total cost (block fixed cost, car-mile transportation cost, classification handling cost, and interchange cost), with a volume-weighted Stress Score for scenarios where full feasibility is unattainable. All inputs use the [GMNS](https://github.com/zephyr-data-specs/GMNS) format. The full statement is in [`docs/problem_statement.pdf`](docs/problem_statement.pdf) and on the Kaggle page.

---

> **Research benchmark and data provenance notice.** RAS2026-PSC is a research-derived and benchmark-calibrated competition dataset created for the INFORMS RAS 2026 Problem Solving Competition. It is not an operational or proprietary railroad dataset. Demand records were developed using transformed Freight Analysis Framework (FAF)-based freight-flow references; users seeking original FAF data should obtain it directly from the official BTS/FAF sources. Physical network connectivity is research-derived in part from OpenStreetMap and additional competition-specific research curation. Applicable OpenStreetMap attribution and ODbL terms remain with OSM-derived components. Benchmark yard definitions, capacities, costs, and other parameters are research abstractions for algorithmic evaluation and should not be interpreted as current railroad operating data. Participants and users take full responsibility and liability for their use of the materials. See [`DATA_PROVENANCE_AND_USE.md`](DATA_PROVENANCE_AND_USE.md).

---

## Problem instances

The benchmark ships three network-resolution layers (L1, L2, L3) over one shared physical network, each combined with three demand multipliers (0.5×, 1.0×, 2.0×) for a 3 × 3 = 9-case evaluation grid. The multiplier is set through `demand_multiplier` in `setting.csv`; one `demand.csv` is shipped per layer.

### A. Official competition design (as published on the Kaggle overview)

| Attribute | L1 — Super-hump | L2 — Major-flat | L3 — Beyond major flat |
|---|---:|---:|---:|
| Yards (origins) | 21 | 132 | 1,041 |
| OD pairs | 411 | 11,897 | 136,677 |
| Physical nodes / links | 47,193 / 106,570 | 47,193 / 106,570 | 47,193 / 106,570 |
| Carriers | 6 Class I (UP, BNSF, CSX, NS, CN, CPKC) | same | same |
| Commodity types | 5 (merchandise, intermodal, automobile, coal, grain) | 5 | 5 |
| Demand scenarios | 0.5× / 1.0× / 2.0× | 0.5× / 1.0× / 2.0× | 0.5× / 1.0× / 2.0× |

### B. Observed statistics of the archived v2.1 files

Computed directly from the CSV files in this repository (`datasets/l{1,2,3}/`).

| Statistic | L1 | L2 | L3 |
|---|---:|---:|---:|
| `demand.csv` rows | 2,044 | 2,044 | 2,427 |
| Unique origin yards | 74 | 74 | 80 |
| Unique destination yards | 132 | 132 | 414 |
| Unique OD pairs | 1,618 | 1,618 | 1,998 |
| Total demand (cars / 70-day cycle, 1.0×) | 3,123,123 | 3,123,123 | 3,132,664 |
| Rows by block type (Merch / IM / Grain / Auto / Coal) | 1,519 / 327 / 110 / 87 / 1 | 1,519 / 327 / 110 / 87 / 1 | 1,902 / 327 / 110 / 87 / 1 |
| `node.csv` rows (yards) | 47,193 (1,477) | 47,193 (1,477) | 47,193 (1,477) |
| `link.csv` rows | 106,570 | 106,570 | 106,570 |

The official design table (A) and the archived-file statistics (B) describe different notions of the benchmark: (A) is the published competition-layer description and (B) is what the archived v2.1 CSV snapshot contains. In particular, the archived L1 `demand.csv` carries the same demand population as L2, while [`datasets/l1/README.md`](datasets/l1/README.md) records the L1 design target (21 yards, 411 OD pairs, 775 rows). Both are reported here without alteration.

---

## Downloads

| Item | Where | Notes |
|---|---|---|
| `node.csv`, `demand.csv`, `setting.csv`, `yard_car_demand_summary.csv` per layer | in Git, `datasets/l{1,2,3}/` | plain CSV |
| `link.csv` per layer | in Git as `datasets/l{1,2,3}/link.csv.zip` (~19 MB each) | unzip in place (`python unpack.py --links`) |
| Yard-to-yard minimum distance matrix (2,000,906 rows) | in Git as `datasets/yard_to_yard_min_distance.csv.zip` (~14 MB) | identical to the scoring `od_distance_matrix.csv`; `python unpack.py --od` places it |
| Sample solutions, 9 cases | in Git as `scoring/sample_solutions.zip` (~30 MB) | `python unpack.py --samples` |
| JSON schemas and CSV validator | in Git, `datasets/schemas/` | |
| Validator, metric notebook, packing scripts | in Git, `scoring/` | package v2.0 |
| Problem statement | in Git, `docs/problem_statement.pdf` | |
| **Full package** `RAS2026-PSC-v2.1-full.zip` (everything above, uncompressed, plus the 9-case sample `submission.csv`) | [GitHub Release v2.1](https://github.com/asu-trans-ai-lab/RAS2026-PSC/releases/tag/v2.1) | see the Release page for size |
| Checksums | [`SHA256SUMS.txt`](SHA256SUMS.txt) (also attached to the Release) | SHA-256 |

---

## Quick start

```bash
git clone https://github.com/asu-trans-ai-lab/RAS2026-PSC.git
cd RAS2026-PSC
pip install -r requirements.txt
```

Unpack the compressed inputs (link files, OD distance matrix, sample solutions):

```bash
python unpack.py
```

Validate the CSV inputs against the JSON schemas:

```bash
python datasets/schemas/validate_csvs.py
```

Validate one sample solution (feasibility checks, operating cost, stress metrics):

```bash
cd scoring
python fast_validator_v2_0.py solution_result_l1_10.json --od-matrix od_distance_matrix.csv
```

Pack the nine solution JSON files into a Kaggle-style `submission.csv` and sanity-check it:

```bash
python json2csv.py
python submission_check.py
```

Run the scoring metric (same logic as the Kaggle backend metric). Either open `metric_fast_v2_0.ipynb` in Jupyter and run all cells, or execute it headlessly:

```bash
jupyter nbconvert --to notebook --execute metric_fast_v2_0.ipynb --output metric_fast_v2_0_run.ipynb
```

See [`scoring/SCORE_README.md`](scoring/SCORE_README.md) for the validator checks, the JSON naming rule, and the scoring treatment, and [`datasets/DATASET_README.md`](datasets/DATASET_README.md) for every column, unit, and parameter.

---

## Repository layout

| Path | Contents |
|---|---|
| `datasets/DATASET_README.md` | Field-level reference for all input CSV files |
| `datasets/schemas/` | JSON Schema (Draft 2020-12) for each CSV row type and for `solution_result.json`, plus `validate_csvs.py` |
| `datasets/l1/`, `l2/`, `l3/` | Input data per layer with a layer README |
| `datasets/yard_to_yard_min_distance.csv.zip` | Yard-to-yard shortest-path distances on the released network |
| `scoring/` | `fast_validator_v2_0.py`, `metric_fast_v2_0.ipynb`, `json2csv.py`, `submission_check.py`, `solution.csv`, `sample_solutions.zip`, `SCORE_README.md` |
| `docs/` | GitHub Pages landing page, `problem_statement.pdf`, and `header.png` |
| `unpack.py` | Extracts the compressed inputs in place |
| `DATA_PROVENANCE_AND_USE.md`, `NOTICE.md`, `LICENSE-CODE`, `CITATION.cff`, `SHA256SUMS.txt` | Provenance, notices, code license, citation metadata, checksums |

---

## Provenance and use

Read [`DATA_PROVENANCE_AND_USE.md`](DATA_PROVENANCE_AND_USE.md) before using the data. In short: the benchmark is a **research-derived and benchmark-calibrated research benchmark**, not a fully synthetic dataset and not a direct FAF, BTS, or OSM extract; it is released for competition, research, education, reproducibility, and algorithmic evaluation, and upstream components keep their own attribution and license requirements. Short notices are collected in [`NOTICE.md`](NOTICE.md).

---

## Competition leadership

**Competition Chair** — **Xuesong Zhou**, Professor of Transportation Systems, Arizona State University. Email: xzhou74@asu.edu

**Co-Chair** — **Natalia Zuniga Garcia**, Computational Transportation Engineer, Argonne National Laboratory. Email: nzuniga@anl.gov

**Problem Owner** — **Dr. Peiheng Li**, Norfolk Southern Corporation

> Institutional affiliations are provided to identify the competition leadership and problem-development roles. Their listing should not be interpreted as a separate institutional license, sponsorship statement, operational endorsement, or transfer of ownership of the released benchmark.

**Judging committee** (as listed on the Kaggle page): David Hunt (2025 INFORMS President and 2026 Immediate Past-President); Ravindra K. Ahuja; Michael Hewitt (Editor-in-Chief, *Transportation Science*).

Registration and questions during the competition: rasproblemsolving2026@gmail.com (subject line `RASPSC2026`).

---

## Competition timeline (2026)

| Date | Milestone |
|---|---|
| April 23 | Initial release of the problem statement and demo data for pipeline testing |
| May 19 | Official release of the full problem statement, dataset, and evaluation files |
| July 1 | Registration deadline |
| May 11 – August 21 | Q&A period |
| August 21 | Kaggle submission deadline |
| August 24 | Solution paper submission deadline |
| September 7 | Announcement of finalists |
| September 30 | Finalists submit presentation videos |
| October 12–16 | Finalist video conference with the judges |
| November 1–4 | Finalist presentations and winner announcement at the INFORMS Annual Meeting (RAS cluster) |

Prizes: 1st $2,000, 2nd $1,000, 3rd $750 (total $3,750).

---

## Upstream source links

### Freight Analysis Framework (FAF) — demand-side provenance

| Resource | Link |
|---|---|
| Freight Analysis Framework Version 5 (FAF5), main BTS page (primary provenance/download link) | https://www.bts.gov/faf/faf5 |
| FAF5 Data Tabulation Tool | https://faf.ornl.gov/faf5/dtt_total.aspx |
| FAF5.7.1 Regional Database | https://faf.ornl.gov/faf5/data/download_files/FAF5.7.1.zip |
| FAF5.7.1 State Database | https://faf.ornl.gov/faf5/data/download_files/FAF5.7.1_State.zip |
| Permanent FAF5 dataset DOI | https://doi.org/10.21949/1529116 |
| Current BTS FAF portal | https://www.bts.gov/faf |

FAF5 is listed here because it belongs to the provenance family used in developing the RAS 2026 benchmark. The current BTS FAF portal may contain newer FAF generations. Users should not assume that a later FAF release was used to construct the archived RAS 2026 competition data unless explicitly documented. FAF is produced by the U.S. Bureau of Transportation Statistics (BTS), with FAF5 developed with support from the Federal Highway Administration (FHWA).

### OpenStreetMap (OSM) — physical network provenance

| Resource | Link |
|---|---|
| OpenStreetMap copyright and license | https://www.openstreetmap.org/copyright |
| OpenStreetMap Foundation License and Legal FAQ | https://osmfoundation.org/wiki/Licence_and_Legal_FAQ |

**© OpenStreetMap contributors.** OpenStreetMap data is provided under the Open Database License (ODbL) 1.0. OSM-derived components of the benchmark network remain subject to OSM attribution and ODbL terms.

### Related open resources

- GMNS — General Modeling Network Specification: https://github.com/zephyr-data-specs/GMNS
- FreightRail101: https://github.com/jdlph/FreightRail101
- TAP101: https://github.com/jdlph/TAP101

---

## Code license and notices

Project-authored code (`scoring/*.py`, `scoring/metric_fast_v2_0.ipynb`, `datasets/schemas/`, `unpack.py`) is released under the MIT License; see [`LICENSE-CODE`](LICENSE-CODE), which states its scope. **The code license does not apply to the datasets or to third-party-derived data**, and no blanket data license is asserted over the benchmark. Dataset use conditions are in [`DATA_PROVENANCE_AND_USE.md`](DATA_PROVENANCE_AND_USE.md); attribution notices are in [`NOTICE.md`](NOTICE.md).

---

## References

1. Van Dyke C, Meketon M (2015) Railway Blocking Process. In Patty BW, ed. *Handbook of Operations Research Applications at Railroads* (Springer US, Boston, MA), 119–162.
2. Newton HN, Barnhart C, Vance PH (1998) Constructing railroad blocking plans to minimize handling costs. *Transportation Science* 32(4):330–345.
3. Barnhart C, Jin H, Vance PH (2000) Railroad blocking: A network design application. *Operations Research* 48(4):603–614.
4. Ahuja RK, Jha KC, Liu J (2007) Solving real-life railroad blocking problems. *Interfaces* 37(5):404–419.
5. Crainic TG, Hewitt M (2021) Service network design. In Crainic TG, Gendreau M, Gendron B, eds. *Network Design with Applications to Transportation and Logistics* (Springer), 347–382.
6. INFORMS RAS 2019 Problem Solving Competition: Integrated Train Blocking and Shipment Path Optimization (TBSP). https://connect.informs.org/railway-applications/new-item3/problem-solving-competition682/problem-solving-competition2019
7. General Modeling Network Specification (GMNS). https://github.com/zephyr-data-specs/GMNS
8. FreightRail101. https://github.com/jdlph/FreightRail101
9. TAP101. https://github.com/jdlph/TAP101
10. U.S. Bureau of Transportation Statistics (BTS). Freight Analysis Framework (FAF) and national rail network datasets. https://www.bts.gov/faf
