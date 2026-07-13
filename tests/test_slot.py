"""
Tests for slot.py — covers core calculation functions and end-to-end solve().
"""

import csv
from collections import defaultdict
from pathlib import Path

import pytest

from greedy.solver import solve
from packing import (
    break_quantity,
    part_volume_and_weight,
    pkgs_per_bin,
    total_bins_needed,
)

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Helpers to build dict rows matching the CSV schema
# ---------------------------------------------------------------------------


def pkg(l, w, h, wt, units=1):
    return {
        "length_in": str(l),
        "width_in": str(w),
        "height_in": str(h),
        "weight_lb": str(wt),
        "units_per_package": str(units),
    }


def bin_row(L, W, H, cap):
    return {
        "length_in": str(L),
        "width_in": str(W),
        "height_in": str(H),
        "weight_cap_lb": str(cap),
    }


# ---------------------------------------------------------------------------
# pkgs_per_bin
# ---------------------------------------------------------------------------


class TestPkgsPerBin:
    def test_basic_grid_fit(self):
        # 10×10×10 package in 20×20×20 bin → 2×2×2 = 8
        assert pkgs_per_bin(pkg(10, 10, 10, 1), bin_row(20, 20, 20, 1000)) == 8

    def test_weight_is_binding(self):
        # Dim allows 8 but weight cap 1000 / 500 lb = 2
        assert pkgs_per_bin(pkg(10, 10, 10, 500), bin_row(20, 20, 20, 1000)) == 2

    def test_dim_is_binding(self):
        # 10×10×10 in 20×10×10 → 2 by dim, but weight cap would allow many more
        assert pkgs_per_bin(pkg(10, 10, 10, 1), bin_row(20, 10, 10, 1000)) == 2

    def test_rotation_helps(self):
        # 30×10×10 pkg, bin 20×40×20.
        # No rotation: floor(20/30)=0 → 0. With rotation: floor(20/10)*floor(40/30)*floor(20/10)=2*1*2=4
        assert pkgs_per_bin(pkg(30, 10, 10, 1), bin_row(20, 40, 20, 1000)) == 4

    def test_rotation_no_help_when_height_too_tall(self):
        # Height 50 > bin height 20 — can't rotate height
        assert pkgs_per_bin(pkg(10, 10, 50, 1), bin_row(20, 20, 20, 1000)) == 0

    def test_too_large_both_orientations(self):
        # 30×30×10 in 20×20×20 — footprint too big even rotated
        assert pkgs_per_bin(pkg(30, 30, 10, 1), bin_row(20, 20, 20, 1000)) == 0

    def test_exact_fill_one_package(self):
        assert pkgs_per_bin(pkg(20, 20, 20, 1), bin_row(20, 20, 20, 1000)) == 1

    def test_single_package_heavier_than_cap(self):
        # Weight alone makes it infeasible
        assert pkgs_per_bin(pkg(10, 10, 10, 500), bin_row(20, 20, 20, 100)) == 0

    def test_zero_weight_falls_back_to_dim(self):
        # wt=0 shouldn't crash; weight limit treated as infinite so dim wins
        assert pkgs_per_bin(pkg(10, 10, 10, 0), bin_row(20, 20, 20, 1000)) == 8

    def test_real_heavy_pallet_only_fits_floor_spot(self):
        # P0010 pallet: 42×45×31, 2332.98 lb — exceeds Standard Rack (1500) and Bulk Rack (1750)
        heavy_pallet = pkg(42, 45, 31, 2332.98)
        assert (
            pkgs_per_bin(heavy_pallet, bin_row(48, 44, 40, 1500)) == 0
        )  # Standard Rack
        assert pkgs_per_bin(heavy_pallet, bin_row(96, 48, 60, 1750)) == 0  # Bulk Rack
        assert pkgs_per_bin(heavy_pallet, bin_row(96, 96, 90, 10000)) >= 1  # Floor Spot


# ---------------------------------------------------------------------------
# break_quantity
# ---------------------------------------------------------------------------


class TestBreakQuantity:
    def test_problem_statement_example(self):
        # qty=500, pallet=300, case=50 → 1 pallet + 4 cases + 0 eaches
        levels = {
            "pallet": {"units_per_package": "300"},
            "case": {"units_per_package": "50"},
            "each": {"units_per_package": "1"},
        }
        assert break_quantity(500, levels) == (1, 4, 0)

    def test_remainder_falls_to_eaches(self):
        levels = {
            "pallet": {"units_per_package": "300"},
            "case": {"units_per_package": "50"},
            "each": {"units_per_package": "1"},
        }
        assert break_quantity(523, levels) == (1, 4, 23)

    def test_no_pallet_level(self):
        levels = {
            "case": {"units_per_package": "10"},
            "each": {"units_per_package": "1"},
        }
        assert break_quantity(25, levels) == (0, 2, 5)

    def test_each_only(self):
        levels = {"each": {"units_per_package": "1"}}
        assert break_quantity(7, levels) == (0, 0, 7)

    def test_exact_pallet_no_remainder(self):
        levels = {
            "pallet": {"units_per_package": "100"},
            "case": {"units_per_package": "10"},
            "each": {"units_per_package": "1"},
        }
        assert break_quantity(200, levels) == (2, 0, 0)

    def test_quantity_zero(self):
        levels = {
            "pallet": {"units_per_package": "100"},
            "each": {"units_per_package": "1"},
        }
        assert break_quantity(0, levels) == (0, 0, 0)

    def test_quantity_one_becomes_each(self):
        levels = {
            "pallet": {"units_per_package": "100"},
            "case": {"units_per_package": "10"},
            "each": {"units_per_package": "1"},
        }
        assert break_quantity(1, levels) == (0, 0, 1)

    def test_total_units_preserved(self):
        levels = {
            "pallet": {"units_per_package": "144"},
            "case": {"units_per_package": "18"},
            "each": {"units_per_package": "1"},
        }
        qty = 217
        n_p, n_c, n_e = break_quantity(qty, levels)
        assert n_p * 144 + n_c * 18 + n_e == qty


# ---------------------------------------------------------------------------
# total_bins_needed
# ---------------------------------------------------------------------------


class TestTotalBinsNeeded:
    BIG_BIN = bin_row(96, 96, 96, 50000)

    def _levels(self):
        return {
            "pallet": pkg(40, 40, 40, 100, 100),
            "case": pkg(20, 20, 20, 10, 10),
            "each": pkg(10, 10, 10, 1, 1),
        }

    def test_single_each_needs_one_bin(self):
        levels = {"each": pkg(10, 10, 10, 1)}
        assert total_bins_needed(0, 0, 1, levels, self.BIG_BIN) == 1

    def test_infeasible_package_returns_none(self):
        # Pallet is 100×100×100 — bigger than the big bin
        levels = {"pallet": pkg(100, 100, 100, 1), "each": pkg(10, 10, 10, 1)}
        assert total_bins_needed(1, 0, 0, levels, self.BIG_BIN) is None

    def test_all_zero_counts_returns_zero(self):
        assert total_bins_needed(0, 0, 0, self._levels(), self.BIG_BIN) == 0

    def test_each_form_splits_across_bins(self):
        # 10×10×10 in 20×20×20 bin → 8 per bin; 9 eaches → ceil(9/8) = 2 bins
        levels = {"each": pkg(10, 10, 10, 1)}
        assert total_bins_needed(0, 0, 9, levels, bin_row(20, 20, 20, 1000)) == 2

    def test_multiple_forms_bins_summed(self):
        # 1 pallet → 1 bin, 5 cases → 1 bin, 3 eaches → 1 bin = 3 total
        assert total_bins_needed(1, 5, 3, self._levels(), self.BIG_BIN) == 3

    def test_weight_limit_forces_more_bins(self):
        # each pkg weighs 100 lb, bin cap 150 lb → 1 per bin. 3 eaches → 3 bins.
        levels = {"each": pkg(10, 10, 10, 100)}
        assert total_bins_needed(0, 0, 3, levels, bin_row(96, 96, 96, 150)) == 3


# ---------------------------------------------------------------------------
# part_volume_and_weight
# ---------------------------------------------------------------------------


class TestPartVolumeAndWeight:
    def test_single_each(self):
        levels = {"each": pkg(10, 20, 5, 3.5)}
        vol, wt = part_volume_and_weight(0, 0, 2, levels)
        assert vol == pytest.approx(2 * 10 * 20 * 5)
        assert wt == pytest.approx(2 * 3.5)

    def test_mixed_levels(self):
        levels = {
            "pallet": pkg(40, 40, 40, 200),
            "case": pkg(20, 20, 20, 50),
            "each": pkg(10, 10, 10, 5),
        }
        vol, wt = part_volume_and_weight(1, 2, 3, levels)
        assert vol == pytest.approx(
            1 * 40 * 40 * 40 + 2 * 20 * 20 * 20 + 3 * 10 * 10 * 10
        )
        assert wt == pytest.approx(1 * 200 + 2 * 50 + 3 * 5)

    def test_all_zero(self):
        levels = {"each": pkg(10, 10, 10, 5)}
        vol, wt = part_volume_and_weight(0, 0, 0, levels)
        assert vol == 0.0
        assert wt == 0.0


# ---------------------------------------------------------------------------
# Integration — run solve() against the real CSVs
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def solution():
    """Run solve() once per module; reuse results across all integration tests."""
    results, unplaceable, bins_used_by_type, pool = solve()
    return results, unplaceable, bins_used_by_type, pool


class TestSolveIntegration:
    def test_all_parts_placed(self, solution):
        results, unplaceable, _, _ = solution
        assert unplaceable == []
        assert len(results) == 45

    def test_total_bins_used(self, solution):
        results, _, _, _ = solution
        assert sum(r["bins_used"] for r in results) == 113

    def test_pool_not_exceeded(self, solution):
        _, _, bins_used_by_type, _ = solution
        avail = {
            r["bin_type"]: int(r["num_available"])
            for r in csv.DictReader(open(DATA_DIR / "bins.csv"))
        }
        for bt, used in bins_used_by_type.items():
            assert used <= avail[bt], f"{bt}: used {used} > available {avail[bt]}"

    def test_hazmat_routing(self, solution):
        results, _, _, _ = solution
        parts = {
            r["part_id"]: r["hazmat"]
            for r in csv.DictReader(open(DATA_DIR / "parts.csv"))
        }
        bins = {
            r["bin_type"]: r["zone"]
            for r in csv.DictReader(open(DATA_DIR / "bins.csv"))
        }
        for r in results:
            expected_zone = "hazmat" if parts[r["part_id"]] == "Y" else "general"
            assert bins[r["bin_type"]] == expected_zone, (
                f"{r['part_id']}: expected zone {expected_zone}, got {bins[r['bin_type']]}"
            )

    def test_quantity_fully_accounted_for(self, solution):
        results, _, _, _ = solution
        parts = {
            r["part_id"]: int(r["quantity"])
            for r in csv.DictReader(open(DATA_DIR / "parts.csv"))
        }
        pkg_lookup = defaultdict(dict)
        for row in csv.DictReader(open(DATA_DIR / "packaging.csv")):
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
            assert packed == parts[pid], (
                f"{pid}: packed {packed} != csv qty {parts[pid]}"
            )

    def test_packages_fit_in_assigned_bin(self, solution):
        """Each package form physically fits and is within weight cap of its assigned bin."""
        results, _, _, _ = solution
        bins = {r["bin_type"]: r for r in csv.DictReader(open(DATA_DIR / "bins.csv"))}
        pkg_lookup = defaultdict(dict)
        for row in csv.DictReader(open(DATA_DIR / "packaging.csv")):
            pkg_lookup[row["part_id"]][row["level"]] = row

        for r in results:
            pid = r["part_id"]
            b = bins[r["bin_type"]]
            levels = pkg_lookup[pid]
            for level, count in [
                ("pallet", r["n_pallet"]),
                ("case", r["n_case"]),
                ("each", r["n_each"]),
            ]:
                if count == 0:
                    continue
                ppb = pkgs_per_bin(levels[level], b)
                assert ppb > 0, f"{pid} {level} doesn't fit in {r['bin_type']}"
