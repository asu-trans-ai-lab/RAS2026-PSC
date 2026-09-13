# Data Provenance, Attribution, and Use Notice

This notice applies to every dataset, document, and derived artifact in the
`asu-trans-ai-lab/RAS2026-PSC` repository and its GitHub Release packages.

## Research Benchmark — Not Operational Railroad Data

The RAS 2026 Problem Solving Competition datasets are **research-derived and benchmark-calibrated datasets created for algorithmic evaluation**. They should not be interpreted as direct reproductions of any public source dataset, proprietary railroad dataset, or actual railroad operating plan.

The released instances do **not** represent actual or proprietary railroad traffic, capacities, costs, blocking plans, yard operating conditions, or commercial decisions. They are not a direct extract, copy, compression, or reconstruction of any individual upstream dataset or railroad information system.

## Demand-Side Provenance — Freight Analysis Framework (FAF)

The demand side of the benchmark is partially derived from and calibrated against public freight-flow information from the **Freight Analysis Framework (FAF)**, produced by the U.S. Bureau of Transportation Statistics (BTS), with FAF5 developed with support from the Federal Highway Administration (FHWA).

FAF provides public estimates of freight flows by origin, destination, commodity type, and transportation mode.

The RAS 2026 competition datasets do **not** redistribute raw FAF records as competition demand.

FAF-based information was transformed through research procedures including:

- aggregation;
- geographic and network mapping;
- filtering;
- scaling;
- railcar-equivalent conversion; and
- benchmark calibration.

These transformations were used to construct research-derived yard-to-yard commodity demand records for algorithmic evaluation.

Users seeking the original FAF data should obtain it directly from the **official BTS/FAF data sources** rather than treating the RAS benchmark as a substitute for FAF.

### Official FAF public data links

| Resource | Link |
|---|---|
| Freight Analysis Framework Version 5 (FAF5), main BTS page (primary provenance/download link) | https://www.bts.gov/faf/faf5 |
| FAF5 Data Tabulation Tool (interactive extraction and inspection) | https://faf.ornl.gov/faf5/dtt_total.aspx |
| FAF5.7.1 Regional Database | https://faf.ornl.gov/faf5/data/download_files/FAF5.7.1.zip |
| FAF5.7.1 State Database | https://faf.ornl.gov/faf5/data/download_files/FAF5.7.1_State.zip |
| Permanent FAF5 dataset DOI | https://doi.org/10.21949/1529116 |
| Current BTS FAF portal | https://www.bts.gov/faf |

FAF5 is listed here because it belongs to the provenance family used in developing the RAS 2026 benchmark. The current BTS FAF portal may contain newer FAF generations. Users should not assume that a later FAF release was used to construct the archived RAS 2026 competition data unless explicitly documented.

## Supply-Side and Physical Network Provenance — OpenStreetMap and Research Curation

The physical network used by the benchmark is also **research-derived**.

A substantial portion of the underlying spatial connectivity was developed using open-source geographic and network references, including data derived from **OpenStreetMap (OSM)**, followed by additional network processing, filtering, mapping, simplification, and research curation for the railroad blocking benchmark.

OpenStreetMap data is provided under the **Open Database License (ODbL) 1.0**.

**© OpenStreetMap contributors.**

To the extent that specific released network components are derived from OpenStreetMap data and remain subject to the ODbL, the applicable OpenStreetMap attribution and ODbL terms continue to apply.

Nothing in this repository is intended to replace, restrict, or expand the rights and obligations associated with the original OpenStreetMap data.

The resulting benchmark network should therefore **not** be described as:

- a direct OSM extract;
- an official North American railroad network;
- a proprietary railroad network;
- or an operational representation of current railroad infrastructure.

### Official OpenStreetMap links

| Resource | Link |
|---|---|
| OpenStreetMap copyright and license | https://www.openstreetmap.org/copyright |
| OpenStreetMap Foundation License and Legal FAQ | https://osmfoundation.org/wiki/Licence_and_Legal_FAQ |

Recommended attribution: **© OpenStreetMap contributors**.

## Competition-Specific Research Curation

Yard definitions and attributes, network representation, commodity mapping, demand transformations, capacity assumptions, operational parameters, and cost parameters were assembled and calibrated by the competition problem-development team for research and algorithmic evaluation.

These benchmark parameters are abstractions created for the competition.

Their inclusion should not be interpreted as:

- disclosure of proprietary railroad operating data;
- a representation of current railroad operating practice;
- a railroad commercial decision;
- an official freight forecast;
- or an operational planning recommendation.

## Use and Liability

The Problem Solving Competition and any related materials are provided solely for the purposes of this competition, research, education, reproducibility, and algorithmic evaluation.

**Participants and users take full responsibility and liability for their use of the materials.**

The materials are provided without representation that they are suitable for:

- operational railroad planning;
- commercial decision-making;
- safety-critical applications;
- regulatory analysis;
- investment analysis;
- or any other operational use.

## Dataset Use Statement

The benchmark is released for competition, research, education, reproducibility, and algorithmic evaluation. Upstream data and derived components remain subject to applicable source attribution, copyright, database-right, or license requirements.

No blanket data license (for example, CC BY 4.0) is asserted over the datasets in this repository. Project-authored code (validators, schemas, helper scripts) is separately licensed under the MIT License in [`LICENSE-CODE`](LICENSE-CODE); that code license does not extend to the datasets or to third-party-derived data.

## Illustrative Header Image

The map shown at the top of the README and landing page (`docs/header.png`) is "US railway map" by Wikideas1, from Wikimedia Commons (https://commons.wikimedia.org/wiki/File:US_railway_map.webp), dedicated to the public domain under CC0 1.0 Universal; it was created with QGIS using U.S. Bureau of Transportation Statistics data. It is an illustrative overview of the Class I railroad network, intermodal terminals, and RoRo ports. It is **not** the benchmark network and was not used to construct the released data.

## Institutional Roles

Institutional affiliations listed in this repository identify the competition leadership and problem-development roles. Their listing should not be interpreted as a separate institutional license, sponsorship statement, operational endorsement, or transfer of ownership of the released benchmark.

## Citation

> Peiheng Li and Xuesong (Simon) Zhou. *INFORMS RAS 2026 Problem Solving Competition*. Kaggle, 2026.
> https://www.kaggle.com/competitions/informs-ras-2026-problem-solving-competition

Users relying on upstream public source datasets should additionally cite the applicable original sources, including FAF and OpenStreetMap, as appropriate.
