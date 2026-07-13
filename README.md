# Warehouse Slotting Optimization — Solution

## Table of Contents

- [Running the code](#running-the-code)
- [Results](#results)
  - [Greedy](#greedy)
  - [ILP (OR-Tools CP-SAT)](#ilp-or-tools-cp-sat)
  - [Comparison](#comparison)
- [Approach](#approach)
  - [Greedy solver](#greedy-solver)
  - [ILP solver (OR-Tools CP-SAT)](#ilp-solver-or-tools-cp-sat)
- [Edge cases handled](#edge-cases-handled)
- [If a pool ran out](#if-a-pool-ran-out)
- [Project structure](#project-structure)

---

## Running the code

**Requirements:** Python 3.8+, OR-Tools, pytest (tests only).

```bash
# Install dependencies
pip install -r requirements.txt

# Run both solvers — prints summaries and comparison, writes output/*.csv
python3 src/main.py

# Run all 39 tests
pytest tests/ -v
```

The pre-generated output is in `output/` if you want to inspect results without running anything.

---

## Results

Both a **greedy** solver and a **global ILP** solver (OR-Tools CP-SAT) were implemented and compared.

### Greedy

| Metric            | Value                                      |
| ----------------- | ------------------------------------------ |
| Parts placed      | **45 / 45** (100%)                         |
| Total bins used   | **113** (55% of 205 bins across all types) |
| Unplaceable parts | **0**                                      |

| Bin type      | Used | Available | Vol util | Wt util |
| ------------- | ---- | --------- | -------- | ------- |
| Small Shelf   | 0    | 40        | —        | —       |
| Standard Rack | 18   | 60        | 25%      | 25%     |
| Bulk Rack     | 40   | 40        | 20%      | 39%     |
| Floor Spot    | 35   | 35        | 11%      | 11%     |
| Hazmat Rack   | 20   | 30        | 17%      | 20%     |

### ILP (OR-Tools CP-SAT)

| Metric            | Value                                      |
| ----------------- | ------------------------------------------ |
| Parts placed      | **45 / 45** (100%)                         |
| Total bins used   | **107** (52% of 205 bins across all types) |
| Unplaceable parts | **0**                                      |

| Bin type      | Used | Available | Vol util | Wt util |
| ------------- | ---- | --------- | -------- | ------- |
| Small Shelf   | 0    | 40        | —        | —       |
| Standard Rack | 15   | 60        | 20%      | 23%     |
| Bulk Rack     | 37   | 40        | 18%      | 31%     |
| Floor Spot    | 35   | 35        | 13%      | 14%     |
| Hazmat Rack   | 20   | 30        | 17%      | 20%     |

### Comparison

| Metric          | Greedy | ILP   |
| --------------- | ------ | ----- |
| Parts placed    | 45     | 45    |
| Total bins used | 113    | 107   |
| Bins saved      | —      | **6** |
| Wall time       | ~1 ms  | ~7 ms |

The ILP finds the **globally optimal** assignment — 6 fewer bins than greedy by better balancing the Bulk Rack / Floor Spot tradeoff across all parts simultaneously. Both solvers satisfy all four constraints for every part.

> This fulfills the stretch goal from the problem statement: _"an assignment that shares the finite pools optimally (e.g., an integer program)."_

All four constraints (fit, weight, finite pools, hazmat routing) are satisfied for every part.

---

## Approach

### Greedy solver

#### 1. Breaking quantity into packages

For each part, inventory is decomposed **largest-first**: as many full pallets as possible, then cases with the remainder, then loose eaches. This minimizes the number of individual packages and therefore the number of bins needed.

```
Example — P0037, qty 1203, pallet=531 units, case=59 units:
  1203 ÷ 531 = 2 pallets (1062 units), remainder 141
  141  ÷  59 = 2 cases  (118 units),  remainder 23
  23 loose eaches
```

#### 2. Packages-per-bin calculation

For a given package form in a candidate bin type, two limits are computed and the binding one is taken:

- **Dimension limit** — how many fit in a grid layout:
  `floor(L/l) × floor(W/w) × floor(H/h)`, also trying the rotated footprint `(w, l)` since packages may rotate on the floor but not tip on their side.
- **Weight limit** — `floor(bin_weight_cap / package_weight_lb)`

`packages_per_bin = min(dimension_limit, weight_limit)`

If `packages_per_bin == 0` for any package form a part needs, that bin type is **infeasible** for that part.

#### 3. Total bins per part

Since all package forms of a part must go in the same bin type, the bins needed are summed across forms:

```
bins_for_pallets = ceil(n_pallet / pallet_per_bin)
bins_for_cases   = ceil(n_case   / case_per_bin)
bins_for_eaches  = ceil(n_each   / each_per_bin)
total_bins       = sum of the above
```

#### 4. Bin-type selection

For each part, all compatible bin types (matching zone) are scored by `total_bins`. Ties are broken by bin volume — preferring the smallest feasible bin so that large bins remain available for parts that truly need them.

#### 5. Pool management

Parts are assigned in **most-constrained-first** order:

1. Hazmat parts first (only one bin zone available to them)
2. Within each group, largest quantity first (harder to absorb into a dwindling pool)

When the preferred bin type has insufficient remaining bins, the algorithm falls back to the next-best feasible type.

**Complexity:** O(P·B log B + K) time, O(P + K + B) space — where P = #parts, B = #bin types, K = #packaging rows.

---

### ILP solver (OR-Tools CP-SAT)

The ILP formulates bin assignment as a binary integer program solved to **proven global optimality**:

**Variables:** `assign[part, bin_type] ∈ {0, 1}` for each feasible (part, bin_type) pair — 1 if that part is assigned to that bin type.

**Constraints:**

1. Each part assigned to exactly one bin type: `∑_bt assign[p, bt] = 1`
2. Pool capacity per bin type: `∑_p bins_needed[p, bt] × assign[p, bt] ≤ pool[bt]`

**Objective:** minimise `∑_{p,bt} bins_needed[p, bt] × assign[p, bt]`

For this dataset (45 parts × 5 bin types = ≤225 binary variables, 50 constraints), CP-SAT proves optimality in under 10 ms. The solver raises an error if it terminates without proving optimality, so the result is always guaranteed optimal.

**Complexity (model build):** O(P·B + K) time, O(P·B) space.

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

In this run every part was placed, but **Bulk Rack** (40/40) and **Floor Spot** (35/35) were fully exhausted by the greedy solver. If the pools had been tighter and parts were left unplaceable, the options are:

1. **Fall back to the next-best bin type** — the greedy solver already does this automatically when the preferred type runs dry.
2. **Re-optimize globally** — the ILP solver shares the finite pools across all parts simultaneously, avoiding the local-optima exhaustion that greedy ordering can cause. It recovered 3 Bulk Rack bins (40 → 37) and is the right first move when any pool runs short.
3. **Request additional bins** — if even the ILP cannot place all parts, the solver reports exactly which types are over-subscribed and by how many, giving procurement a precise reorder quantity.

---

## Project structure

```
intern_case_study/
├── conftest.py              ← adds src/ to path for test imports
├── requirements.txt         ← ortools
├── data/
│   ├── bins.csv
│   ├── packaging.csv
│   └── parts.csv
├── instructions/
│   └── PROBLEM_STATEMENT.md
├── output/
│   ├── slotting_plan.csv      ← greedy output
│   └── slotting_plan_ilp.csv  ← ILP output
├── src/
│   ├── main.py              ← entry point (runs both solvers + comparison)
│   ├── csv_io.py            ← CSV helpers and data path constants
│   ├── compare.py           ← side-by-side greedy vs ILP printout
│   ├── packing.py           ← pure calculation functions (fit, decomposition, bins needed)
│   ├── report.py            ← summary printing and utilization stats
│   ├── greedy/
│   │   └── solver.py        ← greedy assignment orchestration
│   └── ilp/
│       ├── model.py         ← CP-SAT model: feasibility map + constraint/objective build
│       └── solver.py        ← ILP orchestration (I/O, solve, result extraction)
└── tests/
    ├── test_slot.py     ← 33 unit + integration tests for greedy solver
    └── test_ilp.py      ← 6 correctness + optimality tests for ILP solver
```

Please feel free to reach out at zhou.aa@northeastern.edu for any questions!
