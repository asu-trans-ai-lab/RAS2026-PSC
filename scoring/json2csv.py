import json
import pandas as pd
from pathlib import Path

# This script defines the mapping between Kaggle case IDs and local solution JSON files.
# It converts the selected solution JSON files into the required submission.csv format.

# ID -> solution json path
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

OUTPUT_CSV = "submission.csv"

rows = []

for case_id in range(9):
    json_path = Path(ID_TO_JSON.get(case_id, ""))

    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        status = "loaded"
    else:
        # 文件不存在时保留该 ID，但 data 为空 JSON
        data_str = json.dumps({}, ensure_ascii=False)
        status = "missing -> empty {}"

    rows.append({
        "ID": case_id,
        "data": data_str,
    })

    print(f"ID={case_id}: {status} | {json_path}")

df = pd.DataFrame(rows, columns=["ID", "data"])
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

print(f"\n{OUTPUT_CSV} has been created successfully.")
print("Shape:", df.shape)
print("IDs:", df["ID"].tolist())
print("Data lengths:", df["data"].str.len().tolist())