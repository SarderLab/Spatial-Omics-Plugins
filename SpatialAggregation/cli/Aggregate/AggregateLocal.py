"""Local entrypoint for Spatial Aggregation plugin.

Runs aggregation from local annotation files without requiring a DSA/Girder instance.
"""
import argparse
import sys

from SpatialAggregation.core import resolve_annotations, run_aggregation, save_results

def main():
    parser = argparse.ArgumentParser(
        description="Spatial Aggregation: transfer properties from a base annotation "
                    "(e.g. Spots) to spatially overlapping structures in target annotations."
    )
    parser.add_argument(
        "--base_annotation",
        required=True,
        help="Path to the base annotation file (e.g. Spots GeoJSON/JSON)."
    )
    parser.add_argument(
        "--agg_annotations",
        required=True,
        nargs="+",
        help="One or more paths to target annotation files to aggregate into "
             "(e.g. glomeruli.json tubules.json)."
    )
    parser.add_argument(
        "--output_dir",
        required=True,
        help="Directory to write aggregated output annotation files."
    )
    parser.add_argument(
        "--annotation_group",
        default="Aggregated FTU",
        help="Group label assigned to every output element (default: 'Aggregated FTU')."
    )

    args = parser.parse_args()

    print("Loading base annotation...")
    base_annotations = resolve_annotations(args.base_annotation)
    if not base_annotations:
        print("ERROR: Could not load base annotation.", file=sys.stderr)
        sys.exit(1)
    base_annotation = base_annotations[0]

    print(f"Loading {len(args.agg_annotations)} target annotation(s)...")
    child_annotations = resolve_annotations(args.agg_annotations)
    if not child_annotations:
        print("ERROR: Could not load any target annotations.", file=sys.stderr)
        sys.exit(1)

    child_names = [
        ann.get("properties", {}).get("name", f"annotation_{i}")
        for i, ann in enumerate(child_annotations)
    ]
    print(f"Target annotation names: {child_names}")

    print("Running spatial aggregation...")
    results = run_aggregation(
        child_annotations=child_annotations,
        base_annotation=base_annotation,
child_annotation_names=child_names,
        annotation_group=args.annotation_group,
    )

    saved = save_results(results, args.output_dir)
    print(f"\nDone. {len(saved)} file(s) saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
