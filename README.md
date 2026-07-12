# Warehouse Slotting Optimization — Solution

## Results

| Metric            | Value                                      |
| ----------------- | ------------------------------------------ |
| Parts placed      | **45 / 45** (100%)                         |
| Total bins used   | **113** (55% of 205 bins across all types) |
| Unplaceable parts | **0**                                      |

**Bins used by type:**

| Bin type      | Used | Available | Vol util | Wt util |
| ------------- | ---- | --------- | -------- | ------- |
| Small Shelf   | 0    | 40        | —        | —       |
| Standard Rack | 18   | 60        | 25%      | 25%     |
| Bulk Rack     | 40   | 40        | 20%      | 39%     |
| Floor Spot    | 35   | 35        | 11%      | 11%     |
| Hazmat Rack   | 20   | 30        | 17%      | 20%     |

All four constraints (fit, weight, finite pools, hazmat routing) are satisfied for every part. Every part was successfully placed — no bin pool ran dry before all parts were assigned.

Two pool types were fully exhausted: **Bulk Rack** (40/40) and **Floor Spot** (35/35). The greedy ordering (most-constrained parts first) was key here — had Floor Spot been depleted by lower-priority parts, the heavyweight pallets (P0010, P0021, P0023, P0029, whose pallets exceed 1,750 lb and can only go in Floor Spot) would have had nowhere to go.

---

## Approach

### 1. Breaking quantity into packages

For each part, inventory is decomposed **largest-first**: as many full pallets as possible, then cases with the remainder, then loose eaches. This minimizes the number of individual packages and therefore the number of bins needed.

```
Example — P0037, qty 1203, pallet=531 units, case=59 units:
  1203 ÷ 531 = 2 pallets (1062 units), remainder 141
  141  ÷  59 = 2 cases  (118 units),  remainder 23
  23 loose eaches
```

### 2. Packages-per-bin calculation

For a given package form in a candidate bin type, two limits are computed and the binding one is taken:

- **Dimension limit** — how many fit in a grid layout:
  `floor(L/l) × floor(W/w) × floor(H/h)`, also trying the rotated footprint `(w, l)` since packages may rotate on the floor but not tip on their side.
- **Weight limit** — `floor(bin_weight_cap / package_weight_lb)`

`packages_per_bin = min(dimension_limit, weight_limit)`

If `packages_per_bin == 0` for any package form a part needs, that bin type is **infeasible** for that part.

### 3. Total bins per part

Since all package forms of a part must go in the same bin type, the bins needed are summed across forms:

```
bins_for_pallets = ceil(n_pallet / pallet_per_bin)
bins_for_cases   = ceil(n_case   / case_per_bin)
bins_for_eaches  = ceil(n_each   / each_per_bin)
total_bins       = sum of the above
```

### 4. Bin-type selection

For each part, all compatible bin types (matching zone) are scored by `total_bins`. Ties are broken by bin volume — preferring the smallest feasible bin so that large bins remain available for parts that truly need them.

### 5. Pool management

Parts are assigned greedily in **most-constrained-first** order:

1. Hazmat parts first (only one bin zone available to them)
2. Within each group, largest quantity first (harder to absorb into a dwindling pool)

When the preferred bin type has insufficient remaining bins, the algorithm falls back to the next-best feasible type. All unplaceable parts (none in this run) are reported with the reason.

---

## Edge cases handled

| Case                                                                         | How it's handled                                                                                 |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Package exceeds bin weight cap                                               | `packages_per_bin = 0` → bin type marked infeasible                                              |
| Package dimensions don't fit                                                 | Same — `0` from floor division → infeasible                                                      |
| Very heavy pallets (P0010 at 2,333 lb, P0021 at 3,965 lb, P0023 at 2,424 lb) | Only Floor Spot (10,000 lb cap) is feasible; those parts are prioritized early                   |
| Small Shelf (250 lb cap)                                                     | Too small for almost every part; ends up unused                                                  |
| Hazmat pool (30 bins, 7 parts)                                               | Hazmat parts assigned first; 20 of 30 bins used, no shortfall                                    |
| Bulk Rack / Floor Spot fully exhausted                                       | Greedy order ensures high-priority parts claim them first; all parts placed before pool runs out |

---

## If a pool ran out

If the Bulk Rack or Floor Spot pools were exhausted before all parts could be placed, the options would be:

1. **Fall back to the next-best bin type** — the algorithm already does this automatically.
2. **Request additional bins** — report exactly which types are over-subscribed and by how many.
3. **Re-optimize globally** — use an integer program to share the finite pools across all parts simultaneously rather than greedily. This can reduce total bins used and avoid local-optima pool exhaustion (see stretch goal in the problem statement).

---

## Project structure

```
intern_case_study/
├── conftest.py          ← adds src/ to path for test imports
├── data/
│   ├── bins.csv
│   ├── packaging.csv
│   └── parts.csv
├── instructions/
│   └── PROBLEM_STATEMENT.md
├── output/
│   └── slotting_plan.csv
├── src/
│   ├── main.py          ← entry point
│   ├── csv_io.py        ← CSV helpers and data path constants
│   ├── packing.py       ← pure calculation functions (fit, decomposition, bins needed)
│   ├── report.py        ← summary printing and utilization stats
│   └── solver.py        ← greedy assignment orchestration
└── tests/
    └── test_slot.py
```

## Running the code

**Requirements:** Python 3.8+, pytest (tests only). No third-party packages needed.

```bash
# Install pytest if you don't have it
pip install pytest

# Run the solver — reads data/*.csv, prints summary, writes output/slotting_plan.csv
python3 src/main.py

# Run the tests
pytest tests/ -v
```

The solver output (slotting plan + summary) is already pre-generated in `output/slotting_plan.csv` if you just want to inspect the results without running anything.

Please feel free to reach out at zhou.aa@northeastern.edu for any questions!
