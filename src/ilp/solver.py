"""
ILP slotting solver — orchestrates data loading, model build, solve, and output.
"""

import time
from collections import defaultdict

from ortools.sat.python import cp_model

from csv_io import DATA_DIR, OUTPUT_DIR, read_csv, write_csv
from report import print_summary

from .model import build_feasibility_map, build_model


def solve_ilp():
    """
    CP-SAT ILP: assign each part to exactly one bin type, minimising total bins used.

    Raises RuntimeError if CP-SAT cannot prove the solution is globally optimal.

    Let P = #parts, B = #bin types, K = #packaging rows.
    Time (end-to-end): O(P · B + K) to build, exponential worst-case to solve —
                       instant in practice for P = 45, B = 5.
    Space: O(P · B).
    """
    parts_rows = read_csv(DATA_DIR / "parts.csv")
    pkg_rows = read_csv(DATA_DIR / "packaging.csv")
    bins_rows = read_csv(DATA_DIR / "bins.csv")

    pkg_levels = defaultdict(dict)
    for row in pkg_rows:
        pkg_levels[row["part_id"]][row["level"]] = row

    pool_sizes = {b["bin_type"]: int(b["num_available"]) for b in bins_rows}
    zones = {
        p["part_id"]: ("hazmat" if p["hazmat"] == "Y" else "general")
        for p in parts_rows
    }

    part_decomps, feasible = build_feasibility_map(
        parts_rows, pkg_levels, bins_rows, zones
    )
    model, assign, unplaceable_pids = build_model(
        parts_rows, bins_rows, feasible, pool_sizes
    )

    solver = cp_model.CpSolver()
    t0 = time.perf_counter()
    status = solver.Solve(model)
    solve_time = time.perf_counter() - t0

    if status == cp_model.FEASIBLE:
        raise RuntimeError(
            "CP-SAT found a solution but could not prove it is optimal "
            "(solver hit a resource limit). Results may be suboptimal."
        )
    if status != cp_model.OPTIMAL:
        raise RuntimeError(
            f"ILP returned status '{solver.StatusName(status)}'. "
            "Pool may be too small to place all parts."
        )

    # Extract results from solution
    results = []
    parts_by_id = {p["part_id"]: p for p in parts_rows}
    for part in parts_rows:
        pid = part["part_id"]
        if pid in unplaceable_pids:
            continue
        n_pallet, n_case, n_each = part_decomps[pid]
        for b in bins_rows:
            bt = b["bin_type"]
            if (pid, bt) in assign and solver.Value(assign[(pid, bt)]) == 1:
                results.append(
                    {
                        "part_id": pid,
                        "bin_type": bt,
                        "n_pallet": n_pallet,
                        "n_case": n_case,
                        "n_each": n_each,
                        "bins_used": feasible[(pid, bt)],
                    }
                )
                break

    unplaceable = [
        {
            "part_id": pid,
            "quantity": parts_by_id[pid]["quantity"],
            "hazmat": parts_by_id[pid]["hazmat"],
            "candidates": [],
            "pool_left": {},
        }
        for pid in sorted(unplaceable_pids)
    ]

    results.sort(key=lambda r: r["part_id"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ilp_csv = OUTPUT_DIR / "slotting_plan_ilp.csv"
    write_csv(
        ilp_csv,
        results,
        ["part_id", "bin_type", "n_pallet", "n_case", "n_each", "bins_used"],
    )
    print_summary(results, unplaceable, bins_rows, pkg_levels, output_path=str(ilp_csv))

    bins_used_by_type = defaultdict(int)
    pool = dict(pool_sizes)
    for r in results:
        bins_used_by_type[r["bin_type"]] += r["bins_used"]
        pool[r["bin_type"]] -= r["bins_used"]

    return results, unplaceable, bins_used_by_type, pool, solve_time
