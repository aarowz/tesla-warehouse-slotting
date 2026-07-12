"""
Summary reporting — prints slotting results and utilization stats to stdout.
"""

from collections import defaultdict

from packing import part_volume_and_weight


def print_summary(results, unplaceable, bins_rows, pkg_levels):
    total_used = sum(r["bins_used"] for r in results)
    total_avail = sum(int(b["num_available"]) for b in bins_rows)

    # Aggregate bins used, volume, and weight per bin type for utilization stats
    bins_used_by_type = defaultdict(int)
    vol_used_by_type = defaultdict(float)
    wt_used_by_type = defaultdict(float)

    for r in results:
        bt = r["bin_type"]
        bins_used_by_type[bt] += r["bins_used"]
        vol, wt = part_volume_and_weight(
            r["n_pallet"], r["n_case"], r["n_each"], pkg_levels[r["part_id"]]
        )
        vol_used_by_type[bt] += vol
        wt_used_by_type[bt] += wt

    print("=" * 60)
    print("SLOTTING SUMMARY")
    print("=" * 60)
    print(f"Parts placed     : {len(results)} / {len(results) + len(unplaceable)}")
    print(f"Parts unplaceable: {len(unplaceable)}")
    print(f"Total bins used  : {total_used} / {total_avail} available")
    print()
    print(f"{'Bin type':<22} {'Used':>5} {'Avail':>6}  {'Vol util':>9}  {'Wt util':>8}")
    print("-" * 60)

    for b in bins_rows:
        bt = b["bin_type"]
        used = bins_used_by_type.get(bt, 0)
        avail = int(b["num_available"])
        bin_vol = float(b["length_in"]) * float(b["width_in"]) * float(b["height_in"])
        bin_cap = float(b["weight_cap_lb"])
        vol_util = (vol_used_by_type[bt] / (used * bin_vol) * 100) if used > 0 else 0.0
        wt_util = (wt_used_by_type[bt] / (used * bin_cap) * 100) if used > 0 else 0.0
        print(
            f"  {bt:<20} {used:>5} / {avail:<4}   {vol_util:>7.1f}%   {wt_util:>7.1f}%"
        )

    if unplaceable:
        print()
        print("UNPLACEABLE PARTS:")
        for u in unplaceable:
            cand_str = (
                ", ".join(
                    f"{b['bin_type']}({n} bins needed, {u['pool_left'].get(b['bin_type'], 0)} avail)"
                    for n, b in u["candidates"]
                )
                or "no feasible bin type"
            )
            print(
                f"  {u['part_id']} (qty={u['quantity']}, hazmat={u['hazmat']}): {cand_str}"
            )
    else:
        print()
        print("All parts successfully placed.")

    print()
    print("Slotting plan written to output/slotting_plan.csv")
