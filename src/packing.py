"""
Pure calculation functions for warehouse slotting — no I/O, no side effects.
"""

import math


def pkgs_per_bin(pkg, bin_row):
    """
    How many packages of one form fit in one bin of one type.
    Packages may rotate on the floor (l/w swap) but height is fixed.
    Returns 0 if the package cannot fit at all.
    """
    l, w, h = float(pkg["length_in"]), float(pkg["width_in"]), float(pkg["height_in"])
    wt = float(pkg["weight_lb"])
    L, W, H = (
        float(bin_row["length_in"]),
        float(bin_row["width_in"]),
        float(bin_row["height_in"]),
    )
    cap = float(bin_row["weight_cap_lb"])

    dim = max(
        math.floor(L / l) * math.floor(W / w) * math.floor(H / h),
        math.floor(L / w) * math.floor(W / l) * math.floor(H / h),
    )
    weight_limit = math.floor(cap / wt) if wt > 0 else dim
    return min(dim, weight_limit)


def break_quantity(quantity, pkg_levels):
    """
    Greedy largest-first decomposition: pallets → cases → eaches.
    Returns (n_pallet, n_case, n_each).
    """
    rem = quantity
    n_pallet = n_case = n_each = 0

    if "pallet" in pkg_levels:
        n_pallet, rem = divmod(rem, int(pkg_levels["pallet"]["units_per_package"]))

    if "case" in pkg_levels:
        n_case, rem = divmod(rem, int(pkg_levels["case"]["units_per_package"]))

    if "each" in pkg_levels:
        n_each, rem = divmod(rem, int(pkg_levels["each"]["units_per_package"]))

    return n_pallet, n_case, n_each


def total_bins_needed(n_pallet, n_case, n_each, pkg_levels, bin_row):
    """
    Total bins of bin_row type needed to store one part's full inventory.
    Returns None if any required package form cannot fit in this bin type.
    """
    total = 0
    for level, count in [("pallet", n_pallet), ("case", n_case), ("each", n_each)]:
        if count == 0:
            continue
        if level not in pkg_levels:
            return None
        ppb = pkgs_per_bin(pkg_levels[level], bin_row)
        if ppb == 0:
            return None
        total += math.ceil(count / ppb)
    return total


def part_volume_and_weight(n_pallet, n_case, n_each, pkg_levels):
    """Total cubic inches and pounds of all packages for one part."""
    vol = wt = 0.0
    for level, count in [("pallet", n_pallet), ("case", n_case), ("each", n_each)]:
        if count == 0:
            continue
        p = pkg_levels[level]
        vol += (
            count * float(p["length_in"]) * float(p["width_in"]) * float(p["height_in"])
        )
        wt += count * float(p["weight_lb"])
    return vol, wt
