"""CLI entrypoint for Spatial Aggregation plugin (DSA/slicer_cli_web).

This is a thin wrapper that handles Girder authentication, data fetching,
and delegates core logic to SpatialAggregation.core.
Kept for backward compatibility with the DSA web UI.
"""
import sys


def get_user_id(gc):
    import girder_client
    try:
        user = gc.get("/user/me")
        if not user:
            token_info = gc.get("/token/current")
            if token_info and "userId" in token_info:
                return token_info["userId"]
            else:
                print("Unable to retrieve user ID from token.")
                return None
        return user["_id"]
    except girder_client.HttpError as e:
        print(f"Authentication failed: {e}")
        return None

def get_user_info(gc, id):
    import girder_client
    try:
        user = gc.get(f'/user/{id}')
        return user
    except girder_client.HttpError as e:
        print(f"Failed to retrieve user info: {e}")
        return None

def get_user_running_jobs(gc, user_id):
    import girder_client
    try:
        jobs = gc.get("job", parameters={
            "userId": user_id,
            "handlers": '["celery_handler"]',
            "statuses": '[2]'
        })
        assert len(jobs) > 0, "No running jobs found for user."
        return jobs
    except girder_client.HttpError as e:
        print(f"Failed to retrieve running jobs: {e}")
        return []

def get_job(gc, title):
    user_id = get_user_id(gc)
    if not user_id:
        print("No user ID found. Cannot retrieve jobs.")
        return None, None
    user = get_user_info(gc, user_id)

    running_jobs = get_user_running_jobs(gc, user_id)
    for job in running_jobs:
        if job["title"] == title:
            return job, user['login']
    print(f"No running jobs found with title '{title}'.")
    return None, user['login']


def main(args):
    import girder_client
    from fusion_tools.handler.dsa_handler import DSAHandler
    from SpatialAggregation.core import run_aggregation

    TITLE = 'Spatial Aggregation'
    sys.stdout.flush()

    # Initialize girder client
    gc = girder_client.GirderClient(
        apiUrl=args.girderApiUrl
    )
    try:
        gc.authenticate(apiKey=args.girderToken)
    except:
        gc.setToken(args.girderToken)

    print('Input arguments: ')
    for a in vars(args):
        print(f'{a}: {getattr(args, a)}')

    # Get job metadata
    job, user_login = get_job(gc, TITLE)
    job_id = job['_id'] if job else 'unknown'
    if job:
        print(f"Using job ID: {job_id} for user: {user_login}")

    # Resolve image ID from file
    file_info = gc.get(f'/file/{args.input_image}')
    image_id = file_info['itemId']

    # Fetch annotations via DSAHandler
    dsa_handler = DSAHandler(girderApiUrl=args.girderApiUrl)
    dsa_handler.gc.setToken(args.girderToken)
    annotations = dsa_handler.get_annotations(item=image_id)

    # Exclude annotations that belong to the "Aggregated FTU" group (previous plugin outputs)
    all_annotation_docs = gc.get(f'/annotation?itemId={image_id}')
    aggregated_ftu_ids = {
        doc['_id']
        for doc in all_annotation_docs
        if doc['annotation'].get('attributes', {}).get('annotation_group') == 'Aggregated FTU'
    }
    annotations = [a for a in annotations if a['properties'].get('_id') not in aggregated_ftu_ids]

    # Select base and child annotations by name
    ann_names = [i['properties']['name'] for i in annotations]
    base_annotation = annotations[ann_names.index(args.base_annotation)]
    child_names = [n.strip() for n in args.agg_annotation.split(',') if n.strip() in ann_names]
    child_annotations = [annotations[ann_names.index(n)] for n in child_names]

    # Run core aggregation logic
    results = run_aggregation(
        child_annotations=child_annotations,
        base_annotation=base_annotation,
        job_id=job_id,
        base_annotation_name=args.base_annotation,
        child_annotation_names=child_names,
        plugin_name=TITLE,
    )

    # Upload results to DSA
    existing_annotations = gc.get(f'/annotation?itemId={image_id}')

    # Delete all existing annotations in the "Aggregated FTU" group
    for existing in existing_annotations:
        if existing['annotation'].get('attributes', {}).get('annotation_group') == 'Aggregated FTU':
            try:
                gc.delete(f'/annotation/{existing["_id"]}')
                print(f'Deleted previous annotation: {existing["annotation"].get("name")} (id: {existing["_id"]})')
            except Exception as e:
                print(f'Failed to delete previous annotation {existing["_id"]}: {e}')

    for result in results:
        ann_name = result["annotation"]["name"]
        gc.post(
            f'/annotation/item/{image_id}',
            json=result
        )
        print(f'Uploaded annotation "{ann_name}" to DSA under "Aggregated FTU"')


if __name__ == '__main__':
    from ctk_cli import CLIArgumentParser
    main(CLIArgumentParser().parse_args())
