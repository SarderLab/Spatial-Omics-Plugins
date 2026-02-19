# Spatial-Omics Plugins

Plugins to support integrative analysis of structures in large histology images and their associated spatial-omics data.

This set of plugins uses [fusion-tools](https://github.com/spborder/fusion-tools/), a package created for the analysis of spatial-omics data and the generation of modular interactive visualization dashboards.

## SpatialAggregation

Transfers properties from a base annotation layer (e.g. Spots with spatial omics data) to spatially overlapping structures in target annotation layers (e.g. glomeruli, tubules).

### Installation

**For Jupyter notebook / local use (no Girder dependencies):**

```bash
pip install .
```

**For DSA/Girder CLI plugin use (includes Girder dependencies):**

```bash
pip install .[dsa]
```

**For full installation (all dependencies):**

```bash
pip install .[all]
```

### Usage (Jupyter Notebook / Python)

```python
from SpatialAggregation import run_aggregation, resolve_annotations, save_results

# Load annotations from files
base = resolve_annotations("/path/to/Spots.json")[0]
targets = resolve_annotations([
    "/path/to/tubules.json",
    "/path/to/arteries_arterioles.json",
])

# Run spatial aggregation
results = run_aggregation(
    child_annotations=targets,
    base_annotation=base,
    job_id="my-analysis-run",
)

# Save results to local files
save_results(results, "./output")
```

### API Reference

| Function | Description |
|----------|-------------|
| `run_aggregation(child_annotations, base_annotation, job_id, ...)` | Run spatial aggregation. Returns list of histomics-format annotation dicts. |
| `resolve_annotations(annotations)` | Load annotations from file paths or pass through in-memory dicts. |
| `load_annotations_from_dir(directory)` | Load all annotation files from a directory. |
| `save_results(results, output_dir)` | Save results as JSON files to a directory. |

### Parameters for `run_aggregation`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `child_annotations` | `list[dict]` | Yes | GeoJSON FeatureCollections to aggregate INTO |
| `base_annotation` | `dict` | Yes | GeoJSON FeatureCollection providing properties |
| `job_id` | `str` | Yes | Job ID/name to identify the run |
| `base_annotation_name` | `str` | No | Name of the base annotation (for logging) |
| `child_annotation_names` | `list[str]` | No | Names for each child annotation (auto-detected if omitted) |
| `plugin_name` | `str` | No | Plugin name in metadata (default: "Spatial Aggregation") |
| `annotation_group` | `str` | No | Group label for elements (default: "Aggregated FTU") |

### Supported Input Formats

`resolve_annotations` and `load_annotations_from_dir` support: `.json`, `.geojson`, `.xml`, `.csv`, `.parquet`

### Docker

**Notebook image (no Girder dependencies):**

```bash
docker build -f Dockerfile.notebook -t spatial-aggregation-notebook .
```

**DSA plugin image (full Girder dependencies):**

```bash
docker build -t spatial-aggregation-dsa .
```

**Running the notebook image with mounted data:**

```bash
docker run --rm \
  -v $(pwd)/test:/data/test \
  -v $(pwd)/output:/app/output \
  spatial-aggregation-notebook \
  python -c "
from SpatialAggregation import run_aggregation, resolve_annotations, save_results

base = resolve_annotations('/data/test/Spots.json')[0]
targets = resolve_annotations([
    '/data/test/tubules.json',
    '/data/test/arteries_arterioles.json',
])

results = run_aggregation(child_annotations=targets, base_annotation=base, job_id='my-run')
save_results(results, '/app/output')
"
```

Or create a `test_container.py` with the above code and run:

```bash
docker run --rm \
  -v $(pwd)/test:/data/test \
  -v $(pwd)/test_container.py:/app/test_container.py \
  -v $(pwd)/output:/app/output \
  spatial-aggregation-notebook \
  python /app/test_container.py
```

### Project Structure

```
Spatial-Omics-Plugins/
├── SpatialAggregation/
│   ├── __init__.py              # Package exports
│   ├── core.py                  # Core aggregation logic (no Girder)
│   └── cli/                     # Legacy DSA/Girder CLI wrapper
│       └── Aggregate/
│           ├── Aggregate.py     # CLI entrypoint for DSA web UI
│           └── Aggregate.xml    # CLI parameter definitions
├── Dockerfile                   # DSA plugin Docker image
├── Dockerfile.notebook          # Lightweight notebook Docker image
└── setup.py                     # Package config with optional deps
```
