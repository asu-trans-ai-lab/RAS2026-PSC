"""unpack.py - Extract the compressed inputs of the RAS2026-PSC archive in place.

Usage (from the repository root):

    python unpack.py            # extract everything
    python unpack.py --links    # only datasets/l{1,2,3}/link.csv.zip
    python unpack.py --od       # only the OD distance matrix into scoring/
    python unpack.py --samples  # only scoring/sample_solutions.zip

What it does:
  1. datasets/l{1,2,3}/link.csv.zip      -> datasets/l{1,2,3}/link.csv
  2. datasets/yard_to_yard_min_distance.csv.zip
                                          -> scoring/od_distance_matrix.csv
     (the two files are byte-identical; the validator and metric notebook
      look for od_distance_matrix.csv next to the scoring scripts)
  3. scoring/sample_solutions.zip         -> scoring/solution_result_l{1,2,3}_{05,10,20}.json

Existing outputs are overwritten. Only the Python standard library is used.
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LAYERS = ("l1", "l2", "l3")


def _extract_member(zip_path: Path, member: str, dest: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(member) as src, open(dest, "wb") as dst:
            for chunk in iter(lambda: src.read(1 << 20), b""):
                dst.write(chunk)
    print(f"  {zip_path.relative_to(ROOT)} -> {dest.relative_to(ROOT)}  ({dest.stat().st_size:,} bytes)")


def unpack_links() -> None:
    print("Extracting link files")
    for layer in LAYERS:
        zp = ROOT / "datasets" / layer / "link.csv.zip"
        if not zp.exists():
            print(f"  missing {zp.relative_to(ROOT)} (skipped)")
            continue
        _extract_member(zp, "link.csv", zp.with_name("link.csv"))


def unpack_od() -> None:
    print("Extracting OD distance matrix")
    zp = ROOT / "datasets" / "yard_to_yard_min_distance.csv.zip"
    if not zp.exists():
        print(f"  missing {zp.relative_to(ROOT)} (skipped)")
        return
    _extract_member(zp, "yard_to_yard_min_distance.csv", ROOT / "scoring" / "od_distance_matrix.csv")


def unpack_samples() -> None:
    print("Extracting sample solutions")
    zp = ROOT / "scoring" / "sample_solutions.zip"
    if not zp.exists():
        print(f"  missing {zp.relative_to(ROOT)} (skipped)")
        return
    with zipfile.ZipFile(zp) as zf:
        for member in zf.namelist():
            name = Path(member).name
            if not name.endswith(".json"):
                continue
            _extract_member(zp, member, ROOT / "scoring" / name)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--links", action="store_true", help="only extract link.csv.zip files")
    p.add_argument("--od", action="store_true", help="only extract the OD distance matrix")
    p.add_argument("--samples", action="store_true", help="only extract sample solutions")
    a = p.parse_args(argv)
    do_all = not (a.links or a.od or a.samples)
    if do_all or a.links:
        unpack_links()
    if do_all or a.od:
        unpack_od()
    if do_all or a.samples:
        unpack_samples()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
