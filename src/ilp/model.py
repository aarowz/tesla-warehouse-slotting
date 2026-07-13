"""
CP-SAT model construction for the ILP bin-type assignment problem.
"""

from ortools.sat.python import cp_model

from packing import break_quantity, total_bins_needed


def build_feasibility_map(parts_rows, pkg_levels, bins_rows, zones):
    """
    Precompute which (part, bin_type) pairs are feasible and how many bins each needs.

    Returns:
        part_decomps : {pid: (n_pallet, n_case, n_each)}
        feasible     : {(pid, bin_type): bins_needed}  — only entries where bins_needed > 0

    Time: O(P · B + K). Space: O(P · B).
    """
    part_decomps = {}
    feasible = {}
    for part in parts_rows:
        pid = part["part_id"]
        n_pallet, n_case, n_each = break_quantity(
            int(part["quantity"]), pkg_levels[pid]
        )
        part_decomps[pid] = (n_pallet, n_case, n_each)
        for b in bins_rows:
            if b["zone"] != zones[pid]:
                continue
            needed = total_bins_needed(n_pallet, n_case, n_each, pkg_levels[pid], b)
            if needed is not None and needed > 0:
                feasible[(pid, b["bin_type"])] = needed
    return part_decomps, feasible


def build_model(parts_rows, bins_rows, feasible, pool_sizes):
    """
    Construct the CP-SAT binary ILP model.

    Formulation
    -----------
    Variables  : assign[pid, bt] ∈ {0, 1} for each (pid, bt) in feasible.
    Constraints:
        (1) sum_bt assign[pid, bt] = 1   for each part with ≥1 feasible option
        (2) sum_pid bins_needed[pid, bt] * assign[pid, bt] ≤ pool[bt]  for each bin type
    Objective  : minimise sum_{pid, bt} bins_needed[pid, bt] * assign[pid, bt]

    Returns:
        model            : CpModel
        assign           : {(pid, bt): BoolVar}
        unplaceable_pids : set of part IDs with no feasible bin type

    Time: O(P · B). Space: O(P · B).
    """
    model = cp_model.CpModel()
    assign = {key: model.NewBoolVar(f"x_{key[0]}_{key[1]}") for key in feasible}

    # Constraint (1): each part placed in exactly one bin type
    unplaceable_pids = set()
    for part in parts_rows:
        pid = part["part_id"]
        part_vars = [
            assign[(pid, b["bin_type"])]
            for b in bins_rows
            if (pid, b["bin_type"]) in assign
        ]
        if part_vars:
            model.Add(sum(part_vars) == 1)
        else:
            unplaceable_pids.add(pid)

    # Constraint (2): pool capacity per bin type
    for b in bins_rows:
        bt = b["bin_type"]
        terms = [
            feasible[(pid, bt)] * assign[(pid, bt)]
            for part in parts_rows
            for pid in [part["part_id"]]
            if (pid, bt) in feasible
        ]
        if terms:
            model.Add(sum(terms) <= pool_sizes[bt])

    # Objective: minimise total bins used
    model.Minimize(sum(feasible[k] * assign[k] for k in assign))

    return model, assign, unplaceable_pids
