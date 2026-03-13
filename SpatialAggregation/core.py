"""Core spatial aggregation logic - no Girder/DSA dependencies."""

import os
import json
import tempfile
from typing import Union

from fusion_tools.utils.shapes import spatially_aggregate, export_annotations, load_annotations


def run_aggregation(
    child_annotations: list,
    base_annotation: dict,
    job_id: str = "local",
    base_annotation_name: str = "",
    child_annotation_names: list = None,
    plugin_name: str = "Spatial Aggregation",
    annotation_group: str = "Aggregated FTU",
) -> list:
    """Run spatial aggregation from a base annotation to one or more child annotations.

    Transfers properties from the base annotation (e.g. Spots with spatial omics data)
    to spatially overlapping features in each child annotation (e.g. glomeruli, tubules).

    :param child_annotations: List of GeoJSON FeatureCollection dicts to aggregate INTO.
    :param base_annotation: Single GeoJSON FeatureCollection dict providing properties.
    :param job_id: Job ID/name provided by the user (required).
    :param base_annotation_name: Name of the base annotation (for logging).
    :param child_annotation_names: Names parallel to child_annotations (for output naming).
        If None, extracted from each annotation's properties.name.
    :param plugin_name: Plugin name stored in annotation attributes.
    :param annotation_group: Group label assigned to every element.
    :returns: List of histomics-format annotation dicts, one per child annotation.
    """
    # Derive child names from annotation data if not provided
    if child_annotation_names is None:
        child_annotation_names = [
            ann.get("properties", {}).get("name", f"annotation_{i}")
            for i, ann in enumerate(child_annotations)
        ]

    results = []
    for ann, ann_name in zip(child_annotations, child_annotation_names):
        # Run spatial aggregation
        agged_annotation = spatially_aggregate(
            ann, [base_annotation], separate=False, summarize=False
        )

        # Sanitize name for file path
        safe_name = ann_name.replace("/", "_")

        # Export to histomics format via temp file
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, f"{safe_name}.json")
            export_annotations(
                agged_annotation, format="histomics", save_path=save_path
            )
            with open(save_path, "r") as f:
                formatted_anns = json.load(f)

        # Fix formatting: nested points + stray 'type' in user
        for el in formatted_anns[0]["annotation"]["elements"]:
            if (
                isinstance(el.get("points"), list)
                and len(el["points"]) == 1
                and isinstance(el["points"][0], list)
            ):
                el["points"] = [p for p in el["points"][0] if isinstance(p, list)]

            if "user" in el and "type" in el["user"]:
                del el["user"]["type"]

        # Set metadata attributes
        formatted_anns[0]["annotation"]["attributes"] = {
            "job_id": job_id,
            "plugin": plugin_name,
        }

        # Filter elements without spatial overlap
        original_props = set()
        for feat in ann["features"]:
            if "properties" in feat:
                original_props.update(feat["properties"].keys())

        for ann_doc in formatted_anns:
            original_count = len(ann_doc["annotation"]["elements"])
            ann_doc["annotation"]["elements"] = [
                el
                for el in ann_doc["annotation"]["elements"]
                if "user" in el
                and any(
                    k not in original_props and k != "type"
                    for k in el["user"].keys()
                )
            ]
            filtered_count = len(ann_doc["annotation"]["elements"])
            print(
                f"Filtered elements: {original_count} -> {filtered_count} "
                f"(removed {original_count - filtered_count} without spot overlap)"
            )

        # Set annotation name and group
        for ann_doc in formatted_anns:
            ann_doc["annotation"]["name"] = safe_name
            for el in ann_doc["annotation"]["elements"]:
                el["group"] = annotation_group

        results.append(formatted_anns[0])

    return results


def load_annotations_from_dir(directory: str) -> list:
    """Load all annotation files from a directory.

    Supports .json, .geojson, .xml, .csv, .parquet files.

    :param directory: Path to directory containing annotation files.
    :returns: List of GeoJSON FeatureCollection dicts.
    """
    supported_extensions = {".json", ".geojson", ".xml", ".csv", ".parquet"}
    annotations = []
    for filename in sorted(os.listdir(directory)):
        ext = os.path.splitext(filename)[1].lower()
        if ext in supported_extensions:
            filepath = os.path.join(directory, filename)
            loaded = load_annotations(filepath)
            if isinstance(loaded, list):
                annotations.extend(loaded)
            else:
                annotations.append(loaded)
    return annotations


def resolve_annotations(annotations: Union[list, str]) -> list:
    """Convert a mixed list of GeoJSON dicts or file paths into GeoJSON FeatureCollection dicts.

    Each element can be:
    - A dict (assumed to be a GeoJSON FeatureCollection, passed through)
    - A str file path (.json, .geojson, .xml, .csv, .parquet) loaded via fusion_tools

    :param annotations: List of dicts or file path strings, or a single file path string.
    :returns: List of GeoJSON FeatureCollection dicts.
    """
    if isinstance(annotations, str):
        loaded = load_annotations(annotations)
        return loaded if isinstance(loaded, list) else [loaded]

    resolved = []
    for ann in annotations:
        if isinstance(ann, str):
            loaded = load_annotations(ann)
            if isinstance(loaded, list):
                resolved.extend(loaded)
            else:
                resolved.append(loaded)
        elif isinstance(ann, dict):
            resolved.append(ann)
        else:
            raise TypeError(f"Expected dict or file path str, got {type(ann)}")
    return resolved


def save_results(results: list, output_dir: str) -> list:
    """Save aggregation results to local JSON files.

    :param results: List of histomics-format annotation dicts from run_aggregation().
    :param output_dir: Directory to write output files.
    :returns: List of saved file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    saved = []
    for result in results:
        name = result["annotation"]["name"]
        path = os.path.join(output_dir, f"{name}_aggregated.json")
        with open(path, "w") as f:
            json.dump(result, f, indent=2)
        saved.append(path)
        print(f"Saved: {path}")
    return saved
