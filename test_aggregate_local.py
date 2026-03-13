"""
Test script for AggregateLocal.py.

Fill in the paths below, then run:
    python test_aggregate_local.py
"""
import subprocess
import sys

# ── EDIT THESE ───────────────────────────────────────────────────────────────
BASE_ANNOTATION   = "/path/to/spots.json"          # base annotation (e.g. Spots)
AGG_ANNOTATIONS   = [                               # one or more target annotations
    "/path/to/glomeruli.json",
    "/path/to/tubules.json",
]
OUTPUT_DIR        = "/path/to/output"
# ─────────────────────────────────────────────────────────────────────────────

def run():
    cmd = [
        sys.executable,
        "SpatialAggregation/cli/Aggregate/AggregateLocal.py",
        "--base_annotation", BASE_ANNOTATION,
        "--agg_annotations", *AGG_ANNOTATIONS,
        "--output_dir", OUTPUT_DIR,
    ]

    print("Running command:")
    print(" \\\n  ".join(cmd))
    print()

    result = subprocess.run(cmd, capture_output=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    run()
