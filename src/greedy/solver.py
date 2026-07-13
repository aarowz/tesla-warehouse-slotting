"""
Greedy slotting solver — assigns each part to a bin type, respects all constraints,
and manages the finite bin pool.
"""

from collections import defaultdict

from csv_io import DATA_DIR, OUTPUT_DIR, read_csv, write_csv
from packing import break_quantity, total_bins_needed
from report import print_summary


def solve():
    """
    Greedy slotting: read data, assign each part to a bin type, write results.

    Let P = #parts, B = #bin types, K = #packaging rows (≤ 3P).
    Time:  O(P·B log B + K)
           — sorting parts is O(P log P); per part we score B candidates in
             O(B) and sort them in O(B log B); packaging lookup build is O(K).
    Space: O(P + K + B)
           — pkg_levels dict holds all K rows; pool, sorted_parts, and results
             are each at most O(P) or O(B); candidates list is O(B) per iteration.
    """
    parts_rows = read_csv(DATA_DIR / "parts.csv")
    pkg_rows = read_csv(DATA_DIR / "packaging.csv")
    bins_rows = read_csv(DATA_DIR / "bins.csv")

    # Build per-part packaging lookup: pkg_levels[part_id][level] -> row
    pkg_levels = defaultdict(dict)
    for row in pkg_rows:
        pkg_levels[row["part_id"]][row["level"]] = row

    # Track remaining bins available for each bin type
    pool = {b["bin_type"]: int(b["num_available"]) for b in bins_rows}

    # Assign most-constrained parts first:
    # hazmat parts have only one zone option, so they go before general parts.
    # Within each group, largest quantity first to claim pool space early.
    sorted_parts = sorted(
        parts_rows, key=lambda p: (p["hazmat"] != "Y", -int(p["quantity"]))
    )

    results = []
    unplaceable = []

    for part in sorted_parts:
        pid = part["part_id"]
        qty = int(part["quantity"])
        zone = "hazmat" if part["hazmat"] == "Y" else "general"
        levels = pkg_levels[pid]

        # Decompose quantity into pallets → cases → eaches (greedy largest-first)
        n_pallet, n_case, n_each = break_quantity(qty, levels)

        # Score every bin type in the correct zone; skip infeasible ones (None)
        candidates = []
        for b in bins_rows:
            if b["zone"] != zone:
                continue
            needed = total_bins_needed(n_pallet, n_case, n_each, levels, b)
            if needed is not None:
                candidates.append((needed, b))

        # Prefer fewest bins; break ties by bin volume to save large bins for parts that need them
        candidates.sort(
            key=lambda x: (
                x[0],
                float(x[1]["length_in"])
                * float(x[1]["width_in"])
                * float(x[1]["height_in"]),
            )
        )

        # Assign to the best bin type that still has enough bins in the pool
        placed = False
        for needed, b in candidates:
            bt = b["bin_type"]
            if pool[bt] >= needed:
                pool[bt] -= needed
                results.append(
                    {
                        "part_id": pid,
                        "bin_type": bt,
                        "n_pallet": n_pallet,
                        "n_case": n_case,
                        "n_each": n_each,
                        "bins_used": needed,
                    }
                )
                placed = True
                break

        # If no bin type has enough remaining capacity, record as unplaceable
        if not placed:
            unplaceable.append(
                {
                    "part_id": pid,
                    "quantity": qty,
                    "hazmat": part["hazmat"],
                    "candidates": candidates,
                    "pool_left": {
                        b["bin_type"]: pool[b["bin_type"]]
                        for b in bins_rows
                        if b["zone"] == zone
                    },
                }
            )

    results.sort(key=lambda r: r["part_id"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    greedy_csv = OUTPUT_DIR / "slotting_plan.csv"
    write_csv(
        greedy_csv,
        results,
        ["part_id", "bin_type", "n_pallet", "n_case", "n_each", "bins_used"],
    )
    print_summary(
        results, unplaceable, bins_rows, pkg_levels, output_path=str(greedy_csv)
    )

    bins_used_by_type = defaultdict(int)
    for r in results:
        bins_used_by_type[r["bin_type"]] += r["bins_used"]

    return results, unplaceable, bins_used_by_type, pool
