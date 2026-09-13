# RAS 2026 PSC Scoring Package v2.0

This folder contains the local validation and scoring tools for the RAS 2026 PSC Kaggle evaluation.
The leaderboard uses the same evaluator logic.

If a scoring-script bug is confirmed, the organizing committee will issue a versioned update and clearly document the change.

## Update from v1.0 to v1.1 (May 19)

Version 1.1 adds an explicit demand-volume consistency check to the validator and scoring function.

In particular:

- zero- or negative-volume transportation records are rejected;
- served demand is calculated based on the submitted transported volume, rather than merely by the appearance of a demand in the blocking sequence;
- under-served demand is allowed, but it is penalized through the stress-score unserved car-miles.

This update fixes an issue in v1.0 where zero-volume pseudo-transportation records could be incorrectly counted as served demand.

If a scoring-script bug is confirmed, the organizing committee will issue a versioned update and clearly document the change.

## Update from v1.1 to v2.0 (June 22)

Version 2.0 updates the validator and scoring function to align with the latest interpretation of blocking sequences, direct-only commodity routing, yard-track limits, and interchange-cost calculation.

In particular:

* the yard-track-limit check now counts only classification blocks of type `manifest`, `coal`, and `grain`;
* a new `1b_no_subtour` check is added: a blocking sequence may not revisit the same yard;
* a new `9_direct_block_rule` check is added: Intermodal and Automobile commodities must use a single direct origin-to-destination block;
* the demand transported-volume consistency check from v1.1 is retained and reported as `9b_demand_volume_consistency`;
* the interchange-cost calculation is updated to a per-block two-endpoints Class-I-only rule:

  * for each used block, one interchange is charged only when the origin yard and destination yard belong to different recognized Class-I railroads;
  * intermediate physical-path nodes are ignored in the interchange-cost calculation;
  * railroad labels are normalized, including mapping `CSXT` to `CSX`;
  * missing, connector, or non-Class-I railroad labels are ignored for interchange-cost purposes.



## 0. Archive Note and File Preparation

This repository mirrors the scoring and validation artifacts (package v2.0, June 22, 2026)
released to participants for the competition; see the repository `README.md` for the archive
context and citation.

Two large inputs are shipped compressed and must be unpacked before the commands below run:

```bash
# from the repository root
python unpack.py
```

`unpack.py` extracts `datasets/l{1,2,3}/link.csv.zip` in place, extracts
`datasets/yard_to_yard_min_distance.csv.zip` into `scoring/od_distance_matrix.csv`,
and extracts `scoring/sample_solutions.zip` into `scoring/`. The metric notebook reads the
official `node.csv`, `link.csv`, `demand.csv`, and `setting.csv` from `../datasets/l{1,2,3}/`
relative to this folder, so the raw `link.csv` files must exist.

## 1. Package Contents

| File                     | Description                                                                                                                              |
|--------------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| `fast_validator_v2_0.py`   | Local fast validator. It can directly validate a single `solution_result.json` file.                                                     |
| `metric_fast_v2_0.ipynb`   | Notebook version of the scoring metric. It follows the same logic as the Kaggle backend metric.                                          |
| `json2csv.py`            | Converts multiple solution JSON files into the required Kaggle-style `submission.csv`.                                                   |
| `submission_check.py`    | Performs a basic sanity check on `submission.csv` before scoring.                                                                        |
| `od_distance_matrix.csv` | Yard-to-yard minimum distance matrix used by the validator and metric. **Not stored in Git**: it is byte-identical (SHA-256 verified) to `datasets/yard_to_yard_min_distance.csv.zip`; unzip that file into this folder and rename it to `od_distance_matrix.csv` (see Section 0). It includes a `network_version` column. |
| `solution.csv`           | Case usage/split file used by the metric notebook; this is not a participant submission file.                                             |
| `sample_solutions.zip`   | Example solution JSON files named `solution_result_l{level}_{demand_scale}.json` for use with `fast_validator_v2_0.py` and `metric_fast_v2_0.ipynb`. |

## 2. Version

Current version: **v2.0**


## 3. OD Distance Matrix

`od_distance_matrix.csv` stores the yard-to-yard minimum distances.

The required fields are:

```text
from_yard_id
to_yard_id
min_distance_mile
```

For an OD pair `(origin_yard_id, dest_yard_id)`, the metric uses the direct record:

```text
origin_yard_id -> dest_yard_id
```

It does not overwrite or replace the reverse direction.

In other words, the following two distances are treated as two directed records:

```text
u -> v
v -> u
```

If the two values are different, the metric uses the direction required by the corresponding OD pair.

The matrix is used by the validator and metric for:

1. minimum block volume thresholds;
2. maximum circuitous ratio checks;
3. stress-score calculation for unserved demand.

The OD matrix should be placed in the same folder as the scoring scripts, unless an explicit path is provided to the validator.

## 4. Example JSON Naming Rule

The example solution JSON files follow this naming pattern:

```text
solution_result_l{level}_{demand_scale}.json
```

For example:

```text
solution_result_l1_10.json
solution_result_l2_10.json
solution_result_l3_10.json
```

Here, `10` means the demand multiplier is **1.0**, while `05` --> **0.5** and `20` --> **2.0**.

The three provided `*_10.json` files can be used as examples for the expected JSON format.

## 5. Install Requirements

Install the required packages with:

```bash
pip install -r requirements.txt
```


## 6. Local Validation

To validate a single solution JSON file locally, run:

```bash
python fast_validator_v2_0.py solution_result.json --od-matrix od_distance_matrix.csv
```

For detailed diagnostic output, use:

```bash
python fast_validator_v2_0.py solution_result.json --od-matrix od_distance_matrix.csv --verbose
```

The validator reports:

1. feasibility check results;
2. shortest-path source information;
3. operating cost;
4. stress metrics;
5. final pass/fail status.

A successful validation will print:

```text
ALL VALIDATION CHECKS PASSED
```

## 7. Generate `submission.csv`

To calculate a Kaggle-style score, multiple solution JSON files must first be packed into one `submission.csv`.

Edit the case-to-file mapping in:

```text
json2csv.py
```

The mapping defines which local JSON file corresponds to each Kaggle case ID.

Example:

```python
ID_TO_JSON = {
    0: "solution_result_l1_05.json",
    1: "solution_result_l1_10.json",
    2: "solution_result_l1_20.json",
    3: "solution_result_l2_05.json",
    4: "solution_result_l2_10.json",
    5: "solution_result_l2_20.json",
    6: "solution_result_l3_05.json",
    7: "solution_result_l3_10.json",
    8: "solution_result_l3_20.json",
}
```

Then run:

```bash
python json2csv.py
```

This creates:

```text
submission.csv
```

The script keeps all required case IDs. If a corresponding JSON file is missing, that case is written as an empty JSON object:

```json
{}
```

Empty cases are treated as unsolved by the metric.

## 8. Check `submission.csv`

Before scoring, it is recommended to check the generated submission file:

```bash
python submission_check.py
```

This script checks:

1. the physical number of CSV rows;
2. the required `ID` and `data` columns;
3. the list of case IDs;
4. whether each `data` field is valid JSON;
5. the length of each JSON payload.

A typical output includes:

```text
CSV physical rows
Header
Number of data rows
IDs
DataFrame shape
Columns
ID list
All JSON valid
Data lengths
```

This step helps detect malformed CSV files, missing IDs, or broken JSON strings before running the metric notebook.

## 9. Run the Metric Notebook

After generating and checking `submission.csv`, open:

```text
metric_fast_v2_0.ipynb
```

and run all cells.

The notebook reads:

```text
solution.csv
submission.csv
od_distance_matrix.csv
```

`solution.csv` is the bundled case usage/split file for the metric
notebook. Participants generate `submission.csv`.

and computes the final score using the same logic as the Kaggle backend metric.

The notebook prints per-case information, including:

1. case status;
2. feasibility check summary;
3. shortest-path source;
4. total cost;
5. stress score;
6. case score;
7. global score report.

## 10. Scoring Treatment

The metric uses the following treatment:

| Case status | Scoring treatment |
|---|---|
| Valid non-empty solution | Counted as solved and included in the quality average. |
| Empty `{}` submission | Treated as unsolved. |
| Invalid non-empty submission | Treated as unsolved, same as empty. |

The metric first assigns a ladder interval based on the number of solved cases/scenarios.  
Within the selected interval, the quality component is calculated from the scaled case scores.

## 11. Recommended Workflow

```text
1. Prepare solution JSON files.
2. Validate each JSON locally with fast_validator_v2_0.py.
3. Use json2csv.py to generate submission.csv.
4. Run submission_check.py to verify submission.csv.
5. Run metric_fast_v2_0.ipynb to compute the final score.
```

## 12. Notes

- The local validator and the metric notebook should use the same `od_distance_matrix.csv`.
- Empty `{}` submissions are treated as unsolved cases.
- Invalid non-empty submissions are also treated as unsolved in the scoring metric.
- The scoring package is versioned as **v2.0** to make the validator, notebook, and data interpretation reproducible.
