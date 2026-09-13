"""fast_validator_v2_0.py — Strict-fast validator for RAS v2.0 solutions.

Version: v2.0

Public fast validator v2.0 aligned with the Kaggle metric logic:
- validates solution_result-style JSON files in memory;
- optionally loads od_distance_matrix.csv using DuckDB;
- uses OD matrix distances first, then SciPy sparse Dijkstra for missing OD pairs;
- uses the same combined shortest-path cache for minimum block volume,
  circuitous-ratio checks, and stress-score unserved car-miles;
- includes two-endpoints Class-I interchange-cost calculation.

Usage:
    python fast_validator_v2_0.py solution_result.json
    python fast_validator_v2_0.py solution_result.json --od-matrix path/to/od_distance_matrix.csv
    python fast_validator_v2_0.py solution_result.json --verbose
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import orjson as _orjson
    def _loads(b: bytes):
        try:
            return _orjson.loads(b)
        except Exception:
            return json.loads(b)
except Exception:
    def _loads(b: bytes):
        return json.loads(b)


class ParticipantVisibleError(Exception):
    pass


# Keep these defaults aligned with DATASET_README / setting.csv.
# "demand_multiplier" differ across different case
DEFAULT_SETTINGS = {
    "min_block_vol_short(<100mi)": 350,
    "min_block_vol_med(100-500mi)": 700,
    "min_block_vol_long(>500mi)": 1050,
    "max_circuitous_ratio": 1.3,
    "operating_cycle": 70,
    "block_fixed_cost": 2500.0,
    "transport_cost_coefficient": 1.0,
    "interchange_cost": 100.0,
    "stress_penalty_M": 5.0,
    "demand_multiplier": 1.0,
}


# ---------------------------------------------------------------------------
# Strict-fast validation logic used by metric_fast.
# Updated on 2026-05-17 to align with validator_0517.py:
#   - optionally load od_distance_matrix.csv through DuckDB;
#   - use the OD matrix as the first source for shortest-path distances;
#   - fall back to SciPy sparse Dijkstra for missing OD pairs;
#   - reuse the same OD distances for minimum-volume, circuitous-ratio, and stress-score calculations;
#   - add blocking rule and interchange-cost calculation.
#
# v1.1 update:
#   - stress metrics now use submitted transported volume, not demand-key appearance;
#   - zero/negative blocking-sequence volume is rejected;
#   - transported volume cannot exceed the corresponding input demand volume;
#   - demand origin/destination/type references are checked against input demands.

# v2.0 updates (2026-06-20):
#   - update C2 yard-track-limit classification block types to {"manifest", "coal", "grain"};
#   - add check 1b_no_subtour: a blocking sequence may not revisit the same yard;
#   - add check 9_direct_block_rule: intermodal / automobile must use a single direct OD block;
#   - keep demand transported-volume consistency as check 9b_demand_volume_consistency;
#   - update interchange-cost calculation to the two-endpoints Class-I-only rule:
#       - for each used block, charge one interchange only when the origin and destination yards belong to different recognized Class-I railroads;
#       - ignore intermediate physical-path nodes in the interchange-cost calculation;
#       - normalize Class-I railroad labels, including mapping CSXT to CSX;
# ---------------------------------------------------------------------------


# Change the {"Manifest", "Bulk"} to {"manifest", "coal", "grain"}
# C2 counts only classification blocks under the RAS v2.0 interpretation.
# Intermodal / Auto use separate ramp or auto-facility infrastructure.
CLASSIFICATION_BLOCK_TYPES = {"manifest", "coal", "grain"}


# ---------------------------------------------------------------------------
# Intermodal / Automobile blocks are direct-only.
# ---------------------------------------------------------------------------
def _is_direct_only(commodity_label) -> bool:
    s = str(commodity_label or "").strip().lower()
    return (
        "intermodal" in s
        or "automobile" in s
    )


def _merge_settings(raw_settings: dict | None) -> dict:
    """Merge user settings with defaults and coerce numeric values where possible."""
    settings = {**DEFAULT_SETTINGS, **(raw_settings or {})}
    for k, default in DEFAULT_SETTINGS.items():
        try:
            settings[k] = float(settings[k])
        except (TypeError, ValueError):
            settings[k] = default
    return settings


def _min_vol_scalar(dist: float, s: dict) -> float:
    """RAS threshold rule used by the strict validator: <100, 100--500, >500."""
    if dist < 100:
        return float(s["min_block_vol_short(<100mi)"])
    if dist <= 500:
        return float(s["min_block_vol_med(100-500mi)"])
    return float(s["min_block_vol_long(>500mi)"])


def _parse_arrow_ints(value) -> list[int]:
    if value is None:
        return []
    try:
        if pd.isna(value):
            return []
    except Exception:
        pass
    return [int(x) for x in str(value).split(" -> ") if str(x).strip()]


def _distance_from_link_path(path_value, link_len: dict[int, float]) -> float:
    if path_value is None:
        return 0.0
    try:
        if pd.isna(path_value):
            return 0.0
    except Exception:
        pass

    import re
    tokens = re.findall(r"-?\d+", str(path_value))
    total = 0.0
    for t in tokens:
        lid = int(t)
        total += float(link_len.get(lid, link_len.get(abs(lid), 0.0)))
    return total


def _shortest_path_cache_scipy(links_df: pd.DataFrame, od_pairs: set[tuple[int, int]]) -> dict[tuple[int, int], float]:
    """Compute shortest-path distances using SciPy sparse Dijkstra.

    The reference validator treats physical links as bidirectional. If the input
    already contains both directions, duplicate directed arcs must be coalesced
    before building the CSR matrix, otherwise SciPy will sum duplicate weights.
    For duplicate arcs, keep the minimum length.
    """
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra

    out: dict[tuple[int, int], float] = {}
    if not od_pairs:
        return out

    if links_df.empty or "from_node_id" not in links_df.columns or "to_node_id" not in links_df.columns:
        for u, v in od_pairs:
            out[(int(u), int(v))] = np.nan
        return out

    node_ids = pd.Index(pd.unique(pd.concat([
        links_df["from_node_id"].astype(int),
        links_df["to_node_id"].astype(int),
    ], ignore_index=True)))
    node_to_i = {int(n): i for i, n in enumerate(node_ids)}

    edge_w: dict[tuple[int, int], float] = {}
    for _, l in links_df.iterrows():
        u = int(l["from_node_id"])
        v = int(l["to_node_id"])
        w = float(l["length"])
        iu, iv = node_to_i[u], node_to_i[v]
        for a, b in ((iu, iv), (iv, iu)):
            old_w = edge_w.get((a, b))
            if old_w is None or w < old_w:
                edge_w[(a, b)] = w

    if not edge_w:
        for u, v in od_pairs:
            out[(int(u), int(v))] = np.nan
        return out

    rows = [k[0] for k in edge_w.keys()]
    cols = [k[1] for k in edge_w.keys()]
    data = list(edge_w.values())
    mat = csr_matrix((data, (rows, cols)), shape=(len(node_ids), len(node_ids)))

    by_origin: dict[int, set[int]] = {}
    for u, v in od_pairs:
        by_origin.setdefault(int(u), set()).add(int(v))

    for u, dests in by_origin.items():
        if u not in node_to_i:
            for v in dests:
                out[(u, v)] = np.nan
            continue
        dist = dijkstra(mat, directed=True, indices=node_to_i[u], return_predecessors=False)
        for v in dests:
            out[(u, v)] = float(dist[node_to_i[v]]) if v in node_to_i and np.isfinite(dist[node_to_i[v]]) else np.nan
    return out


def _shortest_path_cache(links_df: pd.DataFrame, od_pairs: set[tuple[int, int]]) -> tuple[dict[tuple[int, int], float], str]:
    """Compute shortest-path distances from the physical network using SciPy."""
    return _shortest_path_cache_scipy(links_df, od_pairs), "scipy_sparse_dijkstra"


def _candidate_od_matrix_paths() -> list[Path]:
    """Return likely locations of od_distance_matrix.csv in local/Kaggle environments."""
    candidates: list[Path] = []
    for p in [Path("od_distance_matrix.csv"), Path.cwd() / "od_distance_matrix.csv"]:
        if p not in candidates:
            candidates.append(p)

    # for kaggle
    kaggle_input = Path("/kaggle/input/competitions/informs-ras-2026-problem-solving-competition/")
    if kaggle_input.exists():
        try:
            for p in kaggle_input.glob("**/od_distance_matrix.csv"):
                if p not in candidates:
                    candidates.append(p)
        except Exception:
            pass
    return candidates


def _resolve_od_matrix_path(od_distance_matrix_path: str | Path | None = None) -> Path | None:
    """Resolve an explicit or auto-discovered OD distance matrix path."""
    if od_distance_matrix_path is not None:
        p = Path(od_distance_matrix_path)
        return p if p.exists() else None
    for p in _candidate_od_matrix_paths():
        if p.exists():
            return p
    return None


def _load_od_distances_from_matrix(
    blocks_df: pd.DataFrame,
    demands_df: pd.DataFrame,
    od_distance_matrix_path: str | Path | None = None,
    verbose: bool = False,
) -> tuple[dict[tuple[int, int], float], dict]:
    """Load only required OD pairs from od_distance_matrix.csv using DuckDB.

    This mirrors validator_0517.py: construct required block/demand OD pairs,
    perform an INNER JOIN against the large matrix, and store both directions in
    memory. If the file is absent or DuckDB fails, return an empty dictionary so
    callers can fall back to SciPy.
    """
    od_distances: dict[tuple[int, int], float] = {}
    meta = {
        "od_matrix_path": None,
        "od_matrix_found": False,
        "od_matrix_loaded_pairs": 0,
        "od_matrix_error": None,
    }

    dist_file = _resolve_od_matrix_path(od_distance_matrix_path)

    if dist_file is None:
        return od_distances, meta

    meta["od_matrix_path"] = str(dist_file)
    meta["od_matrix_found"] = True

    needed_ods: set[tuple[int, int]] = set()
    if len(blocks_df) and {"from_yard_id", "to_yard_id"}.issubset(blocks_df.columns):
        for _, b in blocks_df.reset_index().iterrows():
            try:
                u, v = int(b["from_yard_id"]), int(b["to_yard_id"])
                needed_ods.add((u, v)); needed_ods.add((v, u))
            except Exception:
                pass
    if len(demands_df) and {"origin_yard_id", "dest_yard_id"}.issubset(demands_df.columns):
        for _, d in demands_df.iterrows():
            try:
                u, v = int(d["origin_yard_id"]), int(d["dest_yard_id"])
                needed_ods.add((u, v)); needed_ods.add((v, u))
            except Exception:
                pass

    if not needed_ods:
        return od_distances, meta

    try:
        import duckdb

        needed_df = (
            pd.DataFrame(list(needed_ods), columns=["u", "v"])
            .drop_duplicates()
            .sort_values(["u", "v"])
            .reset_index(drop=True)
        )

        con = duckdb.connect(database=":memory:")
        try:
            con.execute("PRAGMA enable_progress_bar;")
        except Exception:
            pass
        con.register("needed_df", needed_df)
        abs_dist_file = str(Path(dist_file).resolve()).replace("'", "''")
        query = f"""
            SELECT c.from_yard_id, c.to_yard_id, c.min_distance_mile
            FROM read_csv_auto('{abs_dist_file}') AS c
            INNER JOIN needed_df AS n
                ON c.from_yard_id = n.u AND c.to_yard_id = n.v
            ORDER BY from_yard_id, to_yard_id
        """
        if verbose:
            print(f"Discovered {dist_file}. Accelerating shortest paths with DuckDB...")
            print("  Executing DuckDB query over od_distance_matrix.csv...")
        results = con.execute(query).fetchall()
        con.close()

        for u, v, dist in results:
            od_distances[(int(u), int(v))] = float(dist)

        meta["od_matrix_loaded_pairs"] = len(od_distances)
        if verbose:
            print(f"  Loaded {meta['od_matrix_loaded_pairs']} required OD pairs into memory.")
    except Exception as e:
        meta["od_matrix_error"] = str(e)
        if verbose:
            print(f"  Warning: OD matrix load failed ({e}); falling back to SciPy for missing pairs.")

    return od_distances, meta


def _is_valid_sp_distance(u: int, v: int, dist) -> bool:
    """A shortest-path distance is valid if finite and positive, except same-yard OD may be zero."""
    try:
        d = float(dist)
    except (TypeError, ValueError):
        return False
    if pd.isna(d) or not np.isfinite(d):
        return False
    if d < 0:
        return False
    if d == 0 and int(u) != int(v):
        return False
    return True


def _combined_shortest_path_cache(
    links_df: pd.DataFrame,
    od_pairs: set[tuple[int, int]],
    blocks_df: pd.DataFrame,
    demands_df: pd.DataFrame,
    od_distance_matrix_path: str | Path | None = None,
    verbose: bool = False,
) -> tuple[dict[tuple[int, int], float], str, dict]:
    """Use one shortest-path convention everywhere: OD matrix first, SciPy physical-network fallback second.

    Pairs that cannot be obtained from either source remain unresolved and are reported in metadata.
    """
    od_matrix, meta = _load_od_distances_from_matrix(
        blocks_df=blocks_df,
        demands_df=demands_df,
        od_distance_matrix_path=od_distance_matrix_path,
        verbose=verbose,
    )

    requested_pairs = {(int(u), int(v)) for u, v in od_pairs}
    sp_cache: dict[tuple[int, int], float] = {}

    from_matrix = 0
    invalid_matrix = 0
    pairs_for_scipy: set[tuple[int, int]] = set()

    for u, v in requested_pairs:
        if (u, v) in od_matrix and _is_valid_sp_distance(u, v, od_matrix[(u, v)]):
            sp_cache[(u, v)] = float(od_matrix[(u, v)])
            from_matrix += 1
        else:
            if (u, v) in od_matrix:
                invalid_matrix += 1
            pairs_for_scipy.add((u, v))

    scipy_engine_used = False
    from_scipy = 0
    unresolved_after_scipy = 0
    if pairs_for_scipy:
        scipy_cache = _shortest_path_cache_scipy(links_df, pairs_for_scipy)
        scipy_engine_used = True
        for u, v in pairs_for_scipy:
            dist = scipy_cache.get((u, v), np.nan)
            if _is_valid_sp_distance(u, v, dist):
                sp_cache[(u, v)] = float(dist)
                from_scipy += 1
            else:
                unresolved_after_scipy += 1

    if meta.get("od_matrix_found") and meta.get("od_matrix_loaded_pairs", 0) > 0:
        engine = "duckdb_od_matrix"
        if scipy_engine_used:
            engine += "+scipy_sparse_dijkstra_fallback"
    else:
        engine = "scipy_sparse_dijkstra"

    meta["requested_shortest_path_pairs"] = len(requested_pairs)
    meta["shortest_path_pairs_from_matrix"] = from_matrix
    meta["shortest_path_pairs_from_scipy"] = from_scipy
    meta["shortest_path_pairs_unresolved"] = unresolved_after_scipy
    meta["invalid_matrix_pairs_recomputed_by_scipy"] = invalid_matrix
    return sp_cache, engine, meta

def _df_with_columns(records, columns: list[str]) -> pd.DataFrame:
    """Create a DataFrame and ensure required columns exist."""
    df = pd.DataFrame(records or [])
    for c in columns:
        if c not in df.columns:
            df[c] = pd.Series(dtype="object")
    return df


def fast_validate_payload(
    data: dict,
    od_distance_matrix_path: str | Path | None = None,
    verbose: bool = False,
) -> tuple[bool, dict]:
    """Validate a submitted solution_result-style JSON object in memory."""
    if not isinstance(data, dict):
        raise ParticipantVisibleError("Submitted JSON payload must be an object/dict.")
    if "inputs" not in data or "outputs" not in data:
        raise ParticipantVisibleError("Submitted JSON payload must contain both 'inputs' and 'outputs'.")

    settings = _merge_settings(data.get("inputs", {}).get("settings", {}))

    nodes_df = _df_with_columns(data["inputs"].get("nodes", []), [
        "node_id", "node_type", "name", "x_coord", "y_coord",
        "num_tracks", "handling_capacity", "handling_cost",
    ])
    links_df = _df_with_columns(data["inputs"].get("links", []), [
        "link_id", "from_node_id", "to_node_id", "length", "capacity",
    ])
    demands_df = _df_with_columns(data["inputs"].get("demands", []), [
        "commodity_id", "commodity_type", "origin_yard_id", "dest_yard_id", "volume",
    ])

    demand_multiplier = float(settings.get("demand_multiplier", 1.0))
    if "volume" in demands_df.columns and demand_multiplier != 1.0:
        demands_df = demands_df.copy()
        demands_df["volume"] = demands_df["volume"].astype(float) * demand_multiplier

    outputs = data.get("outputs", {})
    blocks_df = _df_with_columns(outputs.get("1 Block Design", []), [
        "block_id", "from_yard_id", "to_yard_id", "block_type",
    ])
    seqs_df = _df_with_columns(outputs.get("2 Blocking Sequence", []), [
        "commodity_id", "commodity_type", "origin_yard_id", "dest_yard_id", "volume", "blocking_sequence",
    ])
    routes_df = _df_with_columns(outputs.get("3 Block Route", []), [
        "block_id", "from_yard_id", "to_yard_id", "physical_path_nodes", "physical_path_links",
    ])

    if "block_type" not in blocks_df.columns and "commodity_type" in blocks_df.columns:
        blocks_df["block_type"] = blocks_df["commodity_type"]

    res = {"checks": {}, "shortest_path_engine": "pending", "od_matrix": {}}
    is_valid = True

    # Index inputs. If the required ID columns are absent or empty, keep empty indexed frames.
    nodes_df = nodes_df.set_index("node_id", drop=True) if "node_id" in nodes_df.columns else nodes_df
    links_df = links_df.set_index("link_id", drop=True) if "link_id" in links_df.columns else links_df
    blocks_df = blocks_df.set_index("block_id", drop=True) if "block_id" in blocks_df.columns else blocks_df

    # ------- [1] Flow conservation -------
    seqs_df = seqs_df.copy()
    seq_split = seqs_df["blocking_sequence"].astype(str).str.split(" -> ") if "blocking_sequence" in seqs_df.columns else pd.Series([], dtype=object)
    seqs_df["bids"] = seq_split.apply(lambda L: [int(x) for x in L if str(x).strip()]) if len(seqs_df) else []
    seqs_df["first_bid"] = seqs_df["bids"].apply(lambda L: L[0] if L else -1) if len(seqs_df) else []
    seqs_df["last_bid"] = seqs_df["bids"].apply(lambda L: L[-1] if L else -1) if len(seqs_df) else []

    bf = blocks_df["from_yard_id"].astype(int).to_dict() if "from_yard_id" in blocks_df.columns else {}
    bt = blocks_df["to_yard_id"].astype(int).to_dict() if "to_yard_id" in blocks_df.columns else {}

    if len(seqs_df):
        seqs_df["seq_origin"] = seqs_df["first_bid"].map(bf)
        seqs_df["seq_dest"] = seqs_df["last_bid"].map(bt)
        bad_orig = seqs_df["seq_origin"].astype("Int64") != seqs_df["origin_yard_id"].astype("Int64")
        bad_dest = seqs_df["seq_dest"].astype("Int64") != seqs_df["dest_yard_id"].astype("Int64")
        n_endpoint_violations = int(bad_orig.sum() + bad_dest.sum())
    else:
        n_endpoint_violations = 0

    chain_violations = 0
    missing_block_refs = 0
    for _, r in seqs_df.iterrows():
        bids = r["bids"]
        if any(bid not in bf or bid not in bt for bid in bids):
            missing_block_refs += 1
            continue
        for i in range(len(bids) - 1):
            if bt.get(bids[i]) != bf.get(bids[i + 1]):
                chain_violations += 1
                break

    edge_set = set()
    if not links_df.empty:
        for _, l in links_df.iterrows():
            u, v = int(l["from_node_id"]), int(l["to_node_id"])
            edge_set.add((u, v)); edge_set.add((v, u))

    physical_od_mismatches = 0
    physical_edge_missing = 0
    route_block_missing = 0
    for _, route in routes_df.iterrows():
        try:
            bid = int(route["block_id"])
        except (KeyError, TypeError, ValueError):
            route_block_missing += 1
            continue
        if bid not in blocks_df.index:
            route_block_missing += 1
            continue
        node_path = _parse_arrow_ints(route.get("physical_path_nodes", ""))
        link_path_str = str(route.get("physical_path_links", "")).strip()
        # Match validator.py: skip empty path records instead of failing here.
        if not node_path or not link_path_str:
            continue
        if node_path[0] != int(blocks_df.loc[bid, "from_yard_id"]) or node_path[-1] != int(blocks_df.loc[bid, "to_yard_id"]):
            physical_od_mismatches += 1
        for u, v in zip(node_path[:-1], node_path[1:]):
            if (u, v) not in edge_set:
                physical_edge_missing += 1
                break

    n1_pass = (
        n_endpoint_violations == 0
        and chain_violations == 0
        and missing_block_refs == 0
        and physical_od_mismatches == 0
        and physical_edge_missing == 0
        and route_block_missing == 0
    )
    res["checks"]["1_flow_conservation"] = {
        "pass": n1_pass,
        "endpoint_mismatches": n_endpoint_violations,
        "chain_break_sequences": chain_violations,
        "missing_block_ref_sequences": missing_block_refs,
        "physical_od_mismatches": physical_od_mismatches,
        "physical_edge_missing": physical_edge_missing,
        "route_block_missing": route_block_missing,
    }
    if not n1_pass:
        is_valid = False

    # ------- [1](b) No-subtour / acyclic blocking sequence -------
    # validator_0601 adds this as part of C1: a blocking sequence may not revisit a yard.
    # Example: A->B->C->B is a cycle/subtour and is invalid.
    n_subtour_violations = 0
    subtour_example = None
    for _, r in seqs_df.iterrows():
        bids = r.get("bids", [])
        if not bids:
            continue
        if any(bid not in bf or bid not in bt for bid in bids):
            continue  # already reported as missing/broken sequence in [1]
        visited_yards = [int(bf[bids[0]])]
        visited_yards.extend(int(bt[bid]) for bid in bids)
        if len(set(visited_yards)) != len(visited_yards):
            n_subtour_violations += 1
            if subtour_example is None:
                subtour_example = " -> ".join(str(y) for y in visited_yards)

    n1b_pass = (n_subtour_violations == 0)
    res["checks"]["1b_no_subtour"] = {
        "pass": n1b_pass,
        "n_violations": int(n_subtour_violations),
        "example_yard_sequence": subtour_example,
    }
    if not n1b_pass:
        is_valid = False

    # ------- [2] Yard track limits -------
    if len(blocks_df) and "block_type" in blocks_df.columns:
        class_types = {str(x).strip().lower() for x in CLASSIFICATION_BLOCK_TYPES}
        is_class = blocks_df["block_type"].astype(str).str.strip().str.lower().isin(class_types)
        class_blocks = blocks_df[is_class]
        out_per_yard = class_blocks.groupby("from_yard_id").size() if len(class_blocks) else pd.Series(dtype=float)
    else:
        out_per_yard = pd.Series(dtype=float)
    nt = nodes_df["num_tracks"].astype(float) if "num_tracks" in nodes_df.columns else pd.Series(dtype=float)
    overuse = (out_per_yard - nt.reindex(out_per_yard.index, fill_value=0)).clip(lower=0) if len(out_per_yard) else pd.Series(dtype=float)
    n_c2_violations = int((overuse > 0).sum()) if len(overuse) else 0
    n2_pass = (n_c2_violations == 0)
    res["checks"]["2_yard_track_limits"] = {
        "pass": n2_pass,
        "n_violations": n_c2_violations,
        "max_overuse": int(overuse.max()) if len(overuse) else 0,
    }
    if not n2_pass:
        is_valid = False

    # ------- [3] Yard handling capacity -------
    interm_records = []
    for _, r in seqs_df.iterrows():
        bids = r["bids"]
        vol = float(r["volume"])
        for bid in bids[1:]:
            interm_records.append((bf.get(bid), vol))
    if interm_records:
        idf = pd.DataFrame(interm_records, columns=["yard_id", "volume"]).dropna()
        handling_vol = idf.groupby("yard_id")["volume"].sum()
    else:
        handling_vol = pd.Series(dtype=float)

    hc = nodes_df["handling_capacity"].astype(float) if "handling_capacity" in nodes_df.columns else pd.Series(dtype=float)

    h_overuse = (handling_vol - hc.reindex(handling_vol.index, fill_value=0)).clip(lower=0) if len(handling_vol) else pd.Series(dtype=float)

    n_c3_violations = int((h_overuse > 0).sum()) if len(h_overuse) else 0
    n3_pass = (n_c3_violations == 0)
    res["checks"]["3_yard_handling_capacity"] = {
        "pass": n3_pass,
        "n_violations": n_c3_violations,
        "max_overuse_cars": float(h_overuse.max()) if len(h_overuse) else 0.0,
    }
    if not n3_pass:
        is_valid = False

    # ------- Actual flow and route distances shared by C4/C5/C6/cost -------
    rows = []
    for _, r in seqs_df.iterrows():
        vol = float(r["volume"])
        for bid in r["bids"]:
            rows.append((bid, vol))
    flow_df = pd.DataFrame(rows, columns=["block_id", "vol"]) if rows else pd.DataFrame(columns=["block_id", "vol"])
    actual_vol = flow_df.groupby("block_id")["vol"].sum() if len(flow_df) else pd.Series(dtype=float)

    link_len = links_df["length"].astype(float).to_dict() if "length" in links_df.columns else {}
    if len(routes_df) and "physical_path_links" in routes_df.columns:
        routes_df = routes_df.copy()
        routes_df["distance"] = routes_df["physical_path_links"].apply(lambda x: _distance_from_link_path(x, link_len))
        bid_dist = routes_df.set_index("block_id")["distance"].to_dict()
    else:
        bid_dist = {}

    used_bids = [int(b) for b, v in actual_vol.items() if float(v) > 0 and int(b) in blocks_df.index]
    od_pairs = {
        (int(blocks_df.loc[bid, "from_yard_id"]), int(blocks_df.loc[bid, "to_yard_id"]))
        for bid in used_bids
    }
    if len(demands_df) and {"origin_yard_id", "dest_yard_id"}.issubset(demands_df.columns):
        for _, d in demands_df.iterrows():
            try:
                od_pairs.add((int(d["origin_yard_id"]), int(d["dest_yard_id"])))
            except Exception:
                pass
    sp_cache, sp_engine, od_meta = _combined_shortest_path_cache(
        links_df=links_df,
        od_pairs=od_pairs,
        blocks_df=blocks_df,
        demands_df=demands_df,
        od_distance_matrix_path=od_distance_matrix_path,
        verbose=verbose,
    )
    res["shortest_path_engine"] = sp_engine
    res["od_matrix"] = od_meta

    if verbose:
        print("[OD MATRIX] path:", od_meta.get("od_matrix_path"))
        print("[OD MATRIX] found:", od_meta.get("od_matrix_found"))
        print("[OD MATRIX] loaded pairs:", od_meta.get("od_matrix_loaded_pairs"))
        print("[OD MATRIX] requested pairs:", od_meta.get("requested_shortest_path_pairs"))
        print("[OD MATRIX] from matrix:", od_meta.get("shortest_path_pairs_from_matrix"))
        print("[OD MATRIX] from scipy:", od_meta.get("shortest_path_pairs_from_scipy"))
        print("[OD MATRIX] engine:", sp_engine)

    # ------- [4] Minimum block volume -------
    min_under_amount = 0.0
    shortest_path_missing_c4 = 0
    n_c4_violations = 0
    for bid in used_bids:
        u = int(blocks_df.loc[bid, "from_yard_id"])
        v = int(blocks_df.loc[bid, "to_yard_id"])
        sp = sp_cache.get((u, v), np.nan)
        if pd.isna(sp) or not np.isfinite(sp) or sp <= 0:
            shortest_path_missing_c4 += 1
            continue
        req_vol = _min_vol_scalar(float(sp), settings)
        b_vol = float(actual_vol.get(bid, 0.0))
        if b_vol < req_vol:
            n_c4_violations += 1
            min_under_amount = max(min_under_amount, req_vol - b_vol)

    n4_pass = (n_c4_violations == 0 and shortest_path_missing_c4 == 0)
    res["checks"]["4_min_block_volume"] = {
        "pass": n4_pass,
        "n_violations": n_c4_violations,
        "shortest_path_missing": shortest_path_missing_c4,
        "max_under_amount": float(min_under_amount),
        "checked_used_blocks": len(used_bids),
    }
    if not n4_pass:
        is_valid = False

    # ------- [5] Link capacities -------
    link_flow = pd.Series(0.0, index=links_df.index, dtype=float) if len(links_df) else pd.Series(dtype=float)
    pairs = []
    for _, r in routes_df.iterrows():
        try:
            bid = int(r["block_id"])
        except Exception:
            continue
        s = r.get("physical_path_links", "")
        if not s:
            continue
        vol = float(actual_vol.get(bid, 0.0))
        if vol == 0:
            continue
        for lid in _parse_arrow_ints(s):
            pairs.append((int(lid), vol))
    if pairs:
        lp = pd.DataFrame(pairs, columns=["link_id", "vol"])
        link_flow = lp.groupby("link_id")["vol"].sum().reindex(links_df.index, fill_value=0)
    cap = links_df["capacity"].astype(float) if "capacity" in links_df.columns else pd.Series(dtype=float)
    util = (link_flow / cap.replace(0, np.nan)).fillna(0) if len(cap) else pd.Series(dtype=float)
    over = link_flow - cap if len(cap) else pd.Series(dtype=float)
    n_c5_violations = int((over > 0).sum()) if len(over) else 0
    n5_pass = (n_c5_violations == 0)
    res["checks"]["5_link_capacity"] = {
        "pass": n5_pass,
        "n_violations": n_c5_violations,
        "max_utilization": float(util.max()) if len(util) else 0.0,
    }
    if not n5_pass:
        is_valid = False

    # ------- [6] Max circuitous ratio -------
    max_ratio = 0.0
    n_c6_violations = 0
    shortest_path_missing_c6 = 0
    for bid in used_bids:
        actual_d = float(bid_dist.get(int(bid), 0.0))
        u = int(blocks_df.loc[bid, "from_yard_id"])
        v = int(blocks_df.loc[bid, "to_yard_id"])
        sp = sp_cache.get((u, v), np.nan)
        if pd.isna(sp) or not np.isfinite(sp) or sp <= 0:
            shortest_path_missing_c6 += 1
            continue
        ratio = actual_d / float(sp)
        max_ratio = max(max_ratio, ratio)
        if actual_d > float(sp) * float(settings["max_circuitous_ratio"]) + 1e-4:
            n_c6_violations += 1
    n6_pass = (n_c6_violations == 0 and shortest_path_missing_c6 == 0)
    res["checks"]["6_max_circuitous_ratio"] = {
        "pass": n6_pass,
        "n_violations": n_c6_violations,
        "shortest_path_missing": shortest_path_missing_c6,
        "max_ratio": round(max_ratio, 4),
    }
    if not n6_pass:
        is_valid = False

    # ------- [7] Single path uniqueness -------
    if "commodity_type" in seqs_df.columns and len(seqs_df):
        grp = seqs_df.groupby(["commodity_id", "commodity_type"])["blocking_sequence"].nunique()
    elif len(seqs_df):
        grp = seqs_df.groupby(["commodity_id"])["blocking_sequence"].nunique()
    else:
        grp = pd.Series(dtype=float)
    n_c7_violations = int((grp > 1).sum()) if len(grp) else 0
    n7_pass = (n_c7_violations == 0)
    res["checks"]["7_single_path_uniqueness"] = {
        "pass": n7_pass,
        "n_split_demands": n_c7_violations,
    }
    if not n7_pass:
        is_valid = False

    # ------- [8] Blocking rule: single commodity type per block -------
    block_type_seen: dict[int, str] = {}
    n_c8_violations = 0
    for _, r in seqs_df.iterrows():
        c_type = str(r.get("commodity_type", "merchandise")).strip().lower()
        for bid in r.get("bids", []):
            bid = int(bid)
            if bid not in blocks_df.index:
                continue
            if bid in block_type_seen and block_type_seen[bid] != c_type:
                n_c8_violations += 1
            else:
                block_type_seen[bid] = c_type
    n8_pass = (n_c8_violations == 0)
    res["checks"]["8_blocking_rule_single_commodity_type"] = {
        "pass": n8_pass,
        "n_mixed_block_type_violations": int(n_c8_violations),
    }
    if not n8_pass:
        is_valid = False

    # ------- [9] Direct-block rule for Intermodal / Automobile  -------
    # validator_0601 rule: these commodity types must use a single OD block.
    n_direct_block_violations = 0
    max_direct_only_blocks_used = 0
    direct_block_example = None
    for _, r in seqs_df.iterrows():
        c_type = str(r.get("commodity_type", ""))
        if not _is_direct_only(c_type):
            continue
        bids = r.get("bids", [])
        max_direct_only_blocks_used = max(max_direct_only_blocks_used, len(bids))
        if len(bids) > 1:
            n_direct_block_violations += 1
            if direct_block_example is None:
                direct_block_example = str(r.get("blocking_sequence", ""))

    n9_direct_pass = (n_direct_block_violations == 0)
    res["checks"]["9_direct_block_rule"] = {
        "pass": n9_direct_pass,
        "n_violations": int(n_direct_block_violations),
        "max_direct_only_blocks_used": int(max_direct_only_blocks_used),
        "example_blocking_sequence": direct_block_example,
    }
    if not n9_direct_pass:
        is_valid = False

    # ------- [9] Demand transported-volume consistency -------
    # A demand is served only by the positive volume actually submitted in
    # "2 Blocking Sequence". Merely appearing in the output must not count as
    # full service. Unserved residual demand is handled by the stress penalty;
    # therefore under-service is not a validation error, but non-positive rows,
    # unknown demand references, OD/type mismatches, and over-service are errors.
    tol = 1e-6
    demand_key_to_info: dict[tuple[int, str], dict] = {}
    if len(demands_df):
        for _, d in demands_df.iterrows():
            try:
                key = (int(d.get("commodity_id", 0)), str(d.get("commodity_type", "")))
                demand_key_to_info[key] = {
                    "volume": float(d.get("volume", 0) or 0),
                    "origin_yard_id": int(d.get("origin_yard_id")),
                    "dest_yard_id": int(d.get("dest_yard_id")),
                }
            except Exception:
                continue

    submitted_volume_by_key: dict[tuple[int, str], float] = {}
    positive_submitted_volume_by_key: dict[tuple[int, str], float] = {}
    n_nonpositive_seq_volume = 0
    n_unknown_demand_refs = 0
    n_demand_od_mismatches = 0

    if len(seqs_df):
        for _, r in seqs_df.iterrows():
            key = (int(r.get("commodity_id", 0)), str(r.get("commodity_type", "")))
            vol = float(r.get("volume", 0) or 0)
            submitted_volume_by_key[key] = submitted_volume_by_key.get(key, 0.0) + vol
            if vol > tol:
                positive_submitted_volume_by_key[key] = positive_submitted_volume_by_key.get(key, 0.0) + vol
            else:
                n_nonpositive_seq_volume += 1

            dem_info = demand_key_to_info.get(key)
            if dem_info is None:
                n_unknown_demand_refs += 1
                continue
            try:
                if (
                    int(r.get("origin_yard_id")) != int(dem_info["origin_yard_id"])
                    or int(r.get("dest_yard_id")) != int(dem_info["dest_yard_id"])
                ):
                    n_demand_od_mismatches += 1
            except Exception:
                n_demand_od_mismatches += 1

    n_overserved_demands = 0
    max_overserved_cars = 0.0
    for key, submitted_v in submitted_volume_by_key.items():
        required_v = float(demand_key_to_info.get(key, {}).get("volume", 0.0))
        over = submitted_v - required_v
        if over > tol:
            n_overserved_demands += 1
            max_overserved_cars = max(max_overserved_cars, over)

    n9_pass = (
        n_nonpositive_seq_volume == 0
        and n_unknown_demand_refs == 0
        and n_demand_od_mismatches == 0
        and n_overserved_demands == 0
    )
    res["checks"]["9b_demand_volume_consistency"] = {
        "pass": n9_pass,
        "nonpositive_sequence_volume_rows": int(n_nonpositive_seq_volume),
        "unknown_demand_references": int(n_unknown_demand_refs),
        "demand_od_mismatches": int(n_demand_od_mismatches),
        "overserved_demands": int(n_overserved_demands),
        "max_overserved_cars": float(max_overserved_cars),
        "note": "Under-served demand is allowed and penalized through stress-score unserved car-miles.",
    }
    if not n9_pass:
        is_valid = False


    # ------- Cost calculation -------
    n_blocks = int(len(blocks_df))
    fixed_cost = n_blocks * float(settings["block_fixed_cost"])
    transport_cost = 0.0
    for bid in blocks_df.index:
        vol = float(actual_vol.get(int(bid), 0.0))
        dist = float(bid_dist.get(int(bid), 0.0))
        transport_cost += vol * dist * float(settings["transport_cost_coefficient"])
    hc_cost_map = nodes_df["handling_cost"].astype(float).to_dict() if "handling_cost" in nodes_df.columns else {}
    handling_cost = float(sum(handling_vol.get(yid, 0) * hc_cost_map.get(yid, 0) for yid in handling_vol.index))

    # v2.0 interchange cost: per-block two-endpoints definition.
    # For each used block, compare origin-yard railroad vs destination-yard railroad. If both are Class-I and different, charge one interchange for
    # that block. Intermediate physical-path nodes are ignored.

    interchange_cost_per_car = float(settings.get("interchange_cost", 100.0))

    def _norm_rr(rr):
        try:
            if rr is None or pd.isna(rr):
                return ""
        except Exception:
            if rr is None:
                return ""
        s = str(rr).strip()
        if s in {"", "nan", "NaN", "None", "NONE", "null", "NULL"}:
            return ""
        try:
            x = float(s)
            if x == -1.0:
                return ""
            if x.is_integer():
                return str(int(x))
        except Exception:
            pass
        return "" if s == "-1" else s

    # The data may encode CSX as CSXT, so both labels normalize to CSX.
    def _class_i_rr(rr):
        rr = _norm_rr(rr).upper()
        if rr == "CSXT":
            rr = "CSX"
        return rr if rr in {"BNSF", "CN", "CSX", "UP", "NS", "CPKC"} else ""

    rr_map = {}
    if "railroad_id" in nodes_df.columns:
        rr_map = {
            int(nid): _norm_rr(row.get("railroad_id", ""))
            for nid, row in nodes_df.iterrows()
        }

    interchange_cost = 0.0
    interchange_transition_count = 0

    if len(blocks_df):
        for bid, vol in actual_vol.items():
            try:
                bid = int(bid)
            except Exception:
                continue
            vol = float(vol)
            if vol <= 0 or bid not in blocks_df.index:
                continue

            origin_yard = int(blocks_df.loc[bid, "from_yard_id"])
            dest_yard = int(blocks_df.loc[bid, "to_yard_id"])
            origin_rr = _class_i_rr(rr_map.get(origin_yard, ""))
            dest_rr = _class_i_rr(rr_map.get(dest_yard, ""))

            if origin_rr and dest_rr and origin_rr != dest_rr:
                interchange_transition_count += 1
                interchange_cost += vol * interchange_cost_per_car

    total_cost = fixed_cost + transport_cost + handling_cost + interchange_cost

    res["cost"] = {
        "fixed": float(fixed_cost),
        "transport": float(transport_cost),
        "handling": float(handling_cost),
        "interchange": float(interchange_cost),
        "total": float(total_cost),
        "interchange_definition": "v2.0 per-block two-endpoints Class-I-only",
        "interchange_transition_count": int(interchange_transition_count),
        "interchange_class_i_set": ["BNSF", "CN", "CSX", "UP", "NS","CPKC"],
    }

    # ------- v2.0/v1.1 stress metrics -------
    # v1.1 fix: served demand is measured by actual submitted positive volume,
    # not by whether a (commodity_id, commodity_type) key appears in the output.
    # This prevents zero-volume pseudo-transportation rows from being counted as
    # fully served demands.
    total_demand_vol = 0.0
    served_demand_vol = 0.0
    unserved_carmiles = 0.0
    M = float(settings.get("stress_penalty_M", 5.0))

    stress_sp_used = 0
    stress_shortest_path_missing = 0
    stress_zero_distance_used = 0
    missing_examples: list[tuple[int, int, int, float]] = []

    for _, d in demands_df.iterrows():
        vol = float(d.get("volume", 0) or 0)
        cid = int(d.get("commodity_id", 0))
        ct = str(d.get("commodity_type", ""))
        key = (cid, ct)
        actual_served = max(0.0, float(positive_submitted_volume_by_key.get(key, 0.0)))
        served_vol = min(actual_served, vol)
        unserved_vol = max(0.0, vol - served_vol)

        total_demand_vol += vol
        served_demand_vol += served_vol

        if unserved_vol > 0:
            try:
                o = int(d["origin_yard_id"])
                dst = int(d["dest_yard_id"])
                d_sp = sp_cache.get((o, dst), np.nan)

                if not _is_valid_sp_distance(o, dst, d_sp):
                    stress_shortest_path_missing += 1
                    if len(missing_examples) < 10:
                        missing_examples.append((cid, o, dst, unserved_vol))
                    continue

                if float(d_sp) == 0.0 and o == dst:
                    stress_zero_distance_used += 1

                stress_sp_used += 1
                unserved_carmiles += unserved_vol * float(d_sp)
            except Exception:
                stress_shortest_path_missing += 1

    if verbose:
        print("[STRESS DIST] shortest path used:", stress_sp_used)
        print("[STRESS DIST] shortest path missing:", stress_shortest_path_missing)
        print("[STRESS DIST] zero-distance same-yard OD used:", stress_zero_distance_used)

    if stress_shortest_path_missing > 0:
        # Do not silently compute a partial stress score. The rule is strictly:
        # OD matrix if available, otherwise SciPy shortest path on the physical network.
        examples = "; ".join(
            f"commodity={cid}, OD={o}->{dst}, volume={vol:g}"
            for cid, o, dst, vol in missing_examples
        )
        raise RuntimeError(
            f"Cannot compute stress score: {stress_shortest_path_missing} unserved demand rows "
            f"do not have a finite shortest-path distance from either the OD matrix or SciPy. "
            f"Examples: {examples}"
        )

    loaded_ratio = served_demand_vol / total_demand_vol if total_demand_vol > 0 else 1.0
    unserved_ratio = 1.0 - loaded_ratio
    stress_score = total_cost + M * unserved_carmiles
    res["stress_metrics"] = {
        "M_penalty_coefficient": M,
        "total_demand_cars": float(total_demand_vol),
        "served_demand_cars": float(served_demand_vol),
        "unserved_demand_cars": float(total_demand_vol - served_demand_vol),
        "loaded_demand_ratio": float(loaded_ratio),
        "unserved_demand_ratio": float(unserved_ratio),
        "unserved_carmiles": float(unserved_carmiles),
        "operating_cost": float(total_cost),
        "stress_score": float(stress_score),
        "shortest_path_distance_used_count": int(stress_sp_used),
        "shortest_path_missing_count": int(stress_shortest_path_missing),
        "zero_distance_same_yard_used_count": int(stress_zero_distance_used),
    }

    res["demand_multiplier"] = demand_multiplier
    res["is_valid"] = bool(is_valid)
    return bool(is_valid), res


def fast_validate_file(
    json_path: str | Path,
    od_distance_matrix_path: str | Path | None = None,
    verbose: bool = False,
) -> tuple[bool, dict]:
    """Validate a solution_result-style JSON file."""
    json_path = Path(json_path)
    with open(json_path, "rb") as f:
        data = _loads(f.read())
    if od_distance_matrix_path is None:
        od_distance_matrix_path = json_path.parent / "od_distance_matrix.csv"
    return fast_validate_payload(
        data,
        od_distance_matrix_path=od_distance_matrix_path,
        verbose=verbose,
    )


def _fmt_money(x: float) -> str:
    return f"$ {float(x):,.2f}"


def _print_report(json_path: Path, is_valid: bool, res: dict, total_runtime_s: float) -> None:
    print(f"\nFAST VALIDATOR v2.0 — {json_path}")
    print(f"Total runtime: {total_runtime_s:.2f} s")
    print(f"Shortest paths: {res.get('shortest_path_engine', 'n/a')}")

    od = res.get("od_matrix", {}) or {}
    print("\nOD matrix / shortest-path source:")
    print(f"  path:            {od.get('od_matrix_path')}")
    print(f"  found:           {od.get('od_matrix_found')}")
    print(f"  loaded pairs:    {od.get('od_matrix_loaded_pairs')}")
    print(f"  requested pairs: {od.get('requested_shortest_path_pairs')}")
    print(f"  from matrix:     {od.get('shortest_path_pairs_from_matrix')}")
    print(f"  from scipy:      {od.get('shortest_path_pairs_from_scipy')}")
    if od.get("od_matrix_error"):
        print(f"  matrix error:    {od.get('od_matrix_error')}")

    print("\nValidation checks:")
    for name, info in res.get("checks", {}).items():
        tag = "PASS" if info.get("pass") else "FAIL"
        kv = ", ".join(f"{k}={v}" for k, v in info.items() if k != "pass")
        print(f"  [{tag}] {name}: {kv}")

    c = res.get("cost", {}) or {}
    print("\nCost calculation:")
    print(f"  Fixed Cost:          {_fmt_money(c.get('fixed', 0.0))}")
    print(f"  Transportation Cost: {_fmt_money(c.get('transport', 0.0))}")
    print(f"  Handling Cost:       {_fmt_money(c.get('handling', 0.0))}")
    print(f"  Interchange Cost:    {_fmt_money(c.get('interchange', 0.0))}")
    print(f"  Interchange Rule:    {c.get('interchange_definition', 'n/a')}")
    print(f"  Class-I transitions: {int(c.get('interchange_transition_count', 0) or 0):,}")
    print("-" * 50)
    print(f"  TOTAL COST:          {_fmt_money(c.get('total', 0.0))}")

    s = res.get("stress_metrics", {}) or {}
    print("\nStress metrics:")
    print(f"  Demand multiplier:      {res.get('demand_multiplier', 1.0)}")
    print(f"  Loaded Demand Ratio:    {float(s.get('loaded_demand_ratio', 0.0)):.4f}  "
          f"({float(s.get('served_demand_cars', 0.0)):,.0f} / {float(s.get('total_demand_cars', 0.0)):,.0f} cars)")
    print(f"  Unserved Demand Ratio:  {float(s.get('unserved_demand_ratio', 0.0)):.4f}  "
          f"({float(s.get('unserved_demand_cars', 0.0)):,.0f} cars; "
          f"{float(s.get('unserved_carmiles', 0.0)):,.0f} car-miles)")
    print(f"  Stress Penalty M:       {s.get('M_penalty_coefficient', 5.0)} $/car-mile")
    print(f"  Stress distance usage:  shortest-path={s.get('shortest_path_distance_used_count', 0)}, "
          f"missing={s.get('shortest_path_missing_count', 0)}, "
          f"zero-distance-same-yard={s.get('zero_distance_same_yard_used_count', 0)}")
    print(f"  STRESS SCORE:           {_fmt_money(s.get('stress_score', 0.0))} "
          f"(= operating + M × unserved_carmiles)")

    print("\n" + "=" * 72)
    if is_valid:
        print("ALL VALIDATION CHECKS PASSED. (fast validator v2.0)")
    else:
        print("VALIDATION FAILED. (fast validator v2.0)")
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="RAS strict-fast public validator v2.0 (per-block two-endpoints interchange).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", help="Path to solution_result.json")
    parser.add_argument(
        "--od-matrix",
        default=None,
        help="Optional explicit path to od_distance_matrix.csv. "
             "If omitted, the validator first checks the JSON directory, then local/Kaggle candidates.",
    )
    parser.add_argument("--quiet", action="store_true", help="Only print PASS/FAIL.")
    parser.add_argument("--verbose", action="store_true", help="Print detailed OD matrix loading diagnostics.")
    args = parser.parse_args()

    t0 = time.time()
    json_path = Path(args.path)
    is_valid, res = fast_validate_file(
        json_path,
        od_distance_matrix_path=args.od_matrix,
        verbose=args.verbose,
    )
    total_runtime_s = time.time() - t0

    if args.quiet:
        print("PASS" if is_valid else "FAIL")
    else:
        _print_report(json_path, is_valid, res, total_runtime_s)

    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
