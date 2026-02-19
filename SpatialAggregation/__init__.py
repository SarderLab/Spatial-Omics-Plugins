"""SpatialAggregation - Spatial omics annotation aggregation toolkit."""

from SpatialAggregation.core import (
    run_aggregation,
    load_annotations_from_dir,
    resolve_annotations,
    save_results,
)

__all__ = [
    "run_aggregation",
    "load_annotations_from_dir",
    "resolve_annotations",
    "save_results",
]
