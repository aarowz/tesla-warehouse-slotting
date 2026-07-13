"""
Entry point — runs greedy and ILP solvers and prints a side-by-side comparison.
"""

import time

from compare import print_comparison
from greedy.solver import solve
from ilp.solver import solve_ilp

if __name__ == "__main__":
    print("=== GREEDY SOLVER ===")
    t0 = time.perf_counter()
    greedy_results, _, _, _ = solve()
    greedy_time = time.perf_counter() - t0

    print()
    print("=== ILP SOLVER (OR-Tools CP-SAT) ===")
    t0 = time.perf_counter()
    ilp_results, _, _, _, _ = solve_ilp()
    ilp_time = time.perf_counter() - t0

    print()
    print_comparison(greedy_results, ilp_results, greedy_time, ilp_time)
