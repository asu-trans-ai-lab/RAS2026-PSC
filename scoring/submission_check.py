import json
import csv
import pandas as pd
import sys

# This script checks the basic structure and validity of the generated submission.csv file.
# It verifies the physical CSV rows, case IDs, columns, JSON parsability, and data field lengths.

csv_path = "submission.csv"
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


with open(csv_path, "r", encoding="utf-8", newline="") as f:
    rows = list(csv.reader(f))

print("CSV physical rows:", len(rows))
print("Header:", rows[0])
print("Number of data rows:", len(rows) - 1)
print("IDs:", [r[0] for r in rows[1:]])


df = pd.read_csv(csv_path)

print("DataFrame shape:", df.shape)
print("Columns:", df.columns.tolist())
print("ID list:", df["ID"].tolist())


ok = []
for i, s in enumerate(df["data"]):
    try:
        obj = json.loads(s)
        ok.append(isinstance(obj, dict))
    except Exception as e:
        print(f"Row {i} JSON parse failed:", e)
        ok.append(False)

print("All JSON valid:", all(ok))
print("Data lengths:", df["data"].str.len().tolist())