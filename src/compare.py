"""
Side-by-side comparison of greedy and ILP slotting solutions.
"""


def print_comparison(greedy_results, ilp_results, greedy_time_s, ilp_time_s):
    """
    Print a table comparing greedy vs ILP on parts placed, bins used, and solve time.
    Highlights parts where the two solvers chose a different bin type.

    Time: O(P log P) — sort and scan placed parts.
    Space: O(P).
    """
    greedy_total = sum(r["bins_used"] for r in greedy_results)
    ilp_total = sum(r["bins_used"] for r in ilp_results)

    greedy_map = {r["part_id"]: r for r in greedy_results}
    ilp_map = {r["part_id"]: r for r in ilp_results}
    all_pids = sorted(set(greedy_map) | set(ilp_map))

    print("=" * 60)
    print("GREEDY vs ILP COMPARISON")
    print("=" * 60)
    print(f"{'Metric':<30} {'Greedy':>10} {'ILP':>10}")
    print("-" * 52)
    print(f"{'Parts placed':<30} {len(greedy_results):>10} {len(ilp_results):>10}")
    print(f"{'Total bins used':<30} {greedy_total:>10} {ilp_total:>10}")
    print(f"{'Bins saved by ILP':<30} {'':>10} {greedy_total - ilp_total:>10}")
    print(f"{'Wall time (s)':<30} {greedy_time_s:>10.4f} {ilp_time_s:>10.4f}")

    diffs = [
        (pid, greedy_map.get(pid), ilp_map.get(pid))
        for pid in all_pids
        if (greedy_map.get(pid) or {}).get("bin_type")
        != (ilp_map.get(pid) or {}).get("bin_type")
        or (greedy_map.get(pid) or {}).get("bins_used")
        != (ilp_map.get(pid) or {}).get("bins_used")
    ]

    print()
    if diffs:
        print(f"Parts with different assignments ({len(diffs)}):")
        print(
            f"  {'Part':<12} {'Greedy bin':<22} {'ILP bin':<22} {'G bins':>7} {'I bins':>7}"
        )
        print("  " + "-" * 72)
        for pid, g, i in diffs:
            g_bt = g["bin_type"] if g else "unplaced"
            i_bt = i["bin_type"] if i else "unplaced"
            g_n = str(g["bins_used"]) if g else "-"
            i_n = str(i["bins_used"]) if i else "-"
            print(f"  {pid:<12} {g_bt:<22} {i_bt:<22} {g_n:>7} {i_n:>7}")
    else:
        print("Greedy and ILP produced identical assignments.")

    print()
