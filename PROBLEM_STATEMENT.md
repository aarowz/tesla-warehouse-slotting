# Case Study: Warehouse Slotting Optimization

## Background

A warehouse stores parts in physical storage **bins**. Bins come in a few
different **types** (shelves, racks, floor spots), each with fixed inside
dimensions, a weight limit, and a limited number of empty bins available.

Right now parts are placed by hand, and space is used inefficiently. Your job is
to design a smarter placement ("slotting") plan that stores all the inventory
using **as few bins as possible**.

You are given three CSV files (all data is synthetic):

- `parts.csv` — the inventory that must be stored
- `packaging.csv` — how each part is packaged (pallet / case / each)
- `bins.csv` — the storage available to store it in

---

## The data

### `parts.csv`
One row per part.

| Column       | Meaning                                              |
|--------------|------------------------------------------------------|
| `part_id`    | Unique part identifier                               |
| `quantity`   | Number of **units** on hand that must be stored      |
| `hazmat`     | `Y` if the part is hazardous, else `N`               |

### `packaging.csv`
One row per **packaging level** of a part. A part can be handled at up to three
levels, and each level has its **own footprint and weight**:

- `each` — a single loose unit (always present; `units_per_package = 1`)
- `case` — a box holding several units
- `pallet` — a pallet holding many units (a multiple of the case)

Not every part has a case or a pallet level.

| Column              | Meaning                                                    |
|---------------------|------------------------------------------------------------|
| `part_id`           | Links to `parts.csv`                                        |
| `level`             | `each`, `case`, or `pallet`                                 |
| `units_per_package` | How many units this package contains                       |
| `length_in`         | Length of this package (inches)                            |
| `width_in`          | Width of this package (inches)                             |
| `height_in`         | Height of this package (inches)                            |
| `weight_lb`         | **Total** weight of one full package (pounds)              |

**You must decide how to break a part's `quantity` into packages.** The intended
approach is largest-first: fill as many **pallets** as possible, then **cases**
with the remainder, then the leftover as loose **eaches**. Example: quantity 500
with pallet = 300 units and case = 50 units → 1 pallet + 4 cases + 0 eaches.

A single part may therefore occupy a **mix** of pallets, cases, and eaches, and
each of those package forms must be slotted (each has its own size and weight).

### `bins.csv`
One row per bin **type**.

| Column          | Meaning                                                     |
|-----------------|-------------------------------------------------------------|
| `bin_type`      | Name of the bin type                                        |
| `length_in`     | Usable inside length (inches)                               |
| `width_in`      | Usable inside width (inches)                                |
| `height_in`     | Usable inside height (inches)                               |
| `weight_cap_lb` | Max **total** weight allowed in one bin of this type        |
| `num_available` | How many empty bins of this type exist (a finite pool)      |
| `zone`          | `general` or `hazmat`                                       |

---

## Objective

Assign **every** part to a bin type and figure out how many bins each part needs,
so that the **total number of bins used across the whole warehouse is minimized**.

---

## Constraints (these are the only rules)

1. **Fit** — every package (pallet, case, or each) must physically fit inside the
   bin. A package may be rotated on the floor (length/width can swap), but not
   tipped on its side (height stays height). You decide how many of each package
   form fit per bin from the dimensions.
2. **Weight** — the total weight of everything placed in a single bin may not
   exceed that bin type's `weight_cap_lb`.
3. **Finite bins** — you cannot use more bins of a type than its `num_available`.
4. **Hazmat routing** — a part with `hazmat = Y` must go in a `hazmat` bin; a
   non-hazmat part must go in a `general` bin.

Assume one part per bin (a single bin holds only one part, though it may hold a
mix of that part's pallets/cases/eaches). Every part must be stored — no part may
be left out.

---

## Deliverables

1. **Code** (Python preferred, any language OK) that reads the three CSVs and
   produces a slotting plan.
2. **A results table** (`slotting_plan.csv`) with one row per part:
   `part_id, bin_type, n_pallet, n_case, n_each, bins_used` — where the package
   counts are how you broke the quantity down, and `bins_used` is how many bins of
   that type the part needs.
3. **A short summary** (a few sentences or a README): total bins used, whether
   every part could be placed within the available pools, and — if not — which
   bin types ran out and what you'd do about it.
4. **A brief write-up of your approach**: how you broke quantity into packages,
   how you decided how many packages fit per bin, and how you chose which bin type
   each part goes to.

---

## How we'll evaluate

- **Correctness** — does the plan respect all four constraints above?
- **Quality** — how few bins does it use?
- **Clarity** — is the code readable and the reasoning easy to follow?
- **Judgment** — how do you handle edge cases (e.g., a part that fits nowhere, or
  a bin pool that runs out)?

We care more about clear thinking and correct constraint handling than about
finding the mathematically perfect answer.

---

## Getting started (suggested path)

1. Break each part's `quantity` into packages (pallets → cases → eaches).
2. For one package form and one bin type, compute how many fit by **dimensions**
   and how many fit by **weight** — the smaller of the two is what one bin holds.
3. Combine the tiers into "bins needed" for that part in that bin type (a part's
   pallets, cases, and eaches all live in bins of the same chosen type).
4. Pick the best feasible bin type for each part (respecting the hazmat rule).
5. Add the finite-pool limit: if a bin type runs out, move parts to the next-best
   feasible type. Report anything that can't be placed.

## Stretch goals (optional)

- Report a **utilization %** per bin (how full each bin is by volume and by
  weight) and the warehouse average.
- Instead of assigning parts one at a time, treat it as a single global
  assignment that shares the finite pools optimally (e.g., an integer program).
