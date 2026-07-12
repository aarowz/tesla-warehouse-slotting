"""
CSV I/O helpers and data path constants.
"""

import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"


def read_csv(path):
    """Read all rows from a CSV into a list of dicts. Time/space: O(n)."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fieldnames):
    """Write rows to a CSV file. Time/space: O(n)."""
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
