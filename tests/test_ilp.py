"""
Integration tests for solve_ilp() — correctness and optimality vs greedy.
"""

from collections import defaultdict

import pytest

from csv_io import DATA_DIR, read_csv
from greedy.solver import solve
from ilp.solver import solve_ilp


@pytest.fixture(scope="module")
def ilp_solution():
    """Run solve_ilp() once per module; reuse results across all tests."""
    return solve_ilp()


@pytest.fixture(scope="module")
def greedy_solution():
    return solve()


class TestILPCorrectness:
    def test_all_parts_placed(self, ilp_solution):
        results, unplaceable, _, _, _ = ilp_solution
        assert unplaceable == []
        assert len(results) == 45

    def test_pool_not_exceeded(self, ilp_solution):
        _, _, bins_used_by_type, _, _ = ilp_solution
        avail = {
            r["bin_type"]: int(r["num_available"])
            for r in read_csv(DATA_DIR / "bins.csv")
        }
        for bt, used in bins_used_by_type.items():
            assert used <= avail[bt], f"{bt}: used {used} > available {avail[bt]}"

    def test_hazmat_zone_routing(self, ilp_solution):
        results, _, _, _, _ = ilp_solution
        parts = {r["part_id"]: r["hazmat"] for r in read_csv(DATA_DIR / "parts.csv")}
        bins = {r["bin_type"]: r["zone"] for r in read_csv(DATA_DIR / "bins.csv")}
        for r in results:
            expected = "hazmat" if parts[r["part_id"]] == "Y" else "general"
            assert bins[r["bin_type"]] == expected, (
                f"{r['part_id']}: expected zone {expected}, got {bins[r['bin_type']]}"
            )

    def test_quantity_fully_accounted_for(self, ilp_solution):
        results, _, _, _, _ = ilp_solution
        parts = {
            r["part_id"]: int(r["quantity"]) for r in read_csv(DATA_DIR / "parts.csv")
        }
        pkg_lookup = defaultdict(dict)
        for row in read_csv(DATA_DIR / "packaging.csv"):
            pkg_lookup[row["part_id"]][row["level"]] = row

        for r in results:
            pid = r["part_id"]
            levels = pkg_lookup[pid]
            upp_p = (
                int(levels["pallet"]["units_per_package"]) if "pallet" in levels else 0
            )
            upp_c = int(levels["case"]["units_per_package"]) if "case" in levels else 0
            upp_e = int(levels["each"]["units_per_package"]) if "each" in levels else 1
            packed = r["n_pallet"] * upp_p + r["n_case"] * upp_c + r["n_each"] * upp_e
            assert packed == parts[pid], f"{pid}: packed {packed} != qty {parts[pid]}"

    def test_solve_time_reasonable(self, ilp_solution):
        _, _, _, _, solve_time = ilp_solution
        assert solve_time < 10.0, f"ILP took {solve_time:.2f}s — unexpectedly slow"


class TestILPOptimality:
    def test_ilp_not_worse_than_greedy(self, ilp_solution, greedy_solution):
        """ILP is proven optimal (solve_ilp raises on non-OPTIMAL status) so it must use ≤ bins than greedy."""
        ilp_total = sum(r["bins_used"] for r in ilp_solution[0])
        greedy_total = sum(r["bins_used"] for r in greedy_solution[0])
        assert ilp_total <= greedy_total, (
            f"ILP used {ilp_total} bins but greedy used {greedy_total}"
        )
