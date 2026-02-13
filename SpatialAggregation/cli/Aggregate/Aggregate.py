"""Plugin for performing spatial aggregation from one set of annotations (aggregator) to another/others
"""
import os
import sys
import numpy as np
import json

import girder_client
from ctk_cli import CLIArgumentParser

from fusion_tools.handler.dsa_handler import DSAHandler
from fusion_tools.utils.shapes import spatially_aggregate, export_annotations

def get_user_id(gc):
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
    try:
        user = gc.get(f'/user/{id}')
        return user
    except girder_client.HttpError as e:
        print(f"Failed to retrieve user info: {e}")
        return None

def get_user_running_jobs(gc, user_id):
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
    TITLE = 'Spatial Aggregation'
    sys.stdout.flush()

    # Initialize girder client
    gc = girder_client.GirderClient(
        apiUrl = args.girderApiUrl
    )
    # Try API key auth first, fall back to session token
    try:
        gc.authenticate(apiKey=args.girderToken)
    except:
        gc.setToken(args.girderToken)

    print('Input arguments: ')
    for a in vars(args):
        print(f'{a}: {getattr(args,a)}')

    job, user_login = get_job(gc, TITLE)
    if job:
        job_id = job['_id']
        print(f"Using job ID: {job_id} for user: {user_login}")

    file_info = gc.get(f'/file/{args.input_image}')
    image_id = file_info['itemId']
    image_name = file_info['name']

    dsa_handler = DSAHandler(
        girderApiUrl=args.girderApiUrl
    )
    annotations = dsa_handler.get_annotations(
        item = image_id
    )

    ann_names = [i['properties']['name'] for i in annotations]
    base_annotation = annotations[ann_names.index(args.base_annotation)]
    agg_annotations = [annotations[ann_names.index(i.strip())] for i in args.agg_annotation.split(',') if i.strip() in ann_names]

    for ann in agg_annotations:
        agged_annotation = spatially_aggregate(ann,[base_annotation],separate=False,summarize=False)

        # Replace "/" with "_" for file saving (but keep original for deletion)
        if "/" in ann['properties']['name']:
            ann['properties']['name'] = ann['properties']['name'].replace('/','_')

        export_annotations(
            agged_annotation,
            format='histomics',
            save_path = os.getcwd()+f'/{ann["properties"]["name"]}.json'
        )

        with open(os.getcwd()+f'/{ann["properties"]["name"]}.json','r') as f:
            formatted_anns = json.load(f)
            f.close()

        # === Fix formatting issues ===
        for el in formatted_anns[0]["annotation"]["elements"]:
            # Fix points structure (unwrap + drop stray 0)
            if isinstance(el.get("points"), list) and len(el["points"]) == 1 and isinstance(el["points"][0], list):
                flat_points = [p for p in el["points"][0] if isinstance(p, list)]
                el["points"] = flat_points
 
            # Remove bad 'type' inside user
            if "user" in el and "type" in el["user"]:
                del el["user"]["type"]

        attributes = {
            "job_id": job_id,
            "plugin": TITLE,
            "user": user_login if user_login else "system"
        }

        formatted_anns[0]['annotation']['attributes'] = attributes

        # Filter out elements that don't overlap with any spots (base annotation)
        # Elements with spot overlap will have aggregated user properties beyond just the original ones
        original_props = set()
        for feat in ann['features']:
            if 'properties' in feat:
                original_props.update(feat['properties'].keys())

        for ann_doc in formatted_anns:
            original_count = len(ann_doc["annotation"]["elements"])
            ann_doc["annotation"]["elements"] = [
                el for el in ann_doc["annotation"]["elements"]
                if "user" in el and any(
                    k not in original_props and k != "type"
                    for k in el["user"].keys()
                )
            ]
            filtered_count = len(ann_doc["annotation"]["elements"])
            print(f'Filtered elements: {original_count} -> {filtered_count} (removed {original_count - filtered_count} without spot overlap)')

        # Name the annotation as {original}_aggregated under the "AggregatedFTU" group
        aggregated_ann_name = f'{ann["properties"]["name"]}'
        aggregated_group = "Aggregated FTU"
        for ann_doc in formatted_anns:
            ann_doc["annotation"]["name"] = aggregated_ann_name
            # Assign each element to the Aggregated FTU group
            for el in ann_doc["annotation"]["elements"]:
                el["group"] = aggregated_group

        # Remove any previous annotation with the same aggregated name to avoid duplicates on re-runs
        existing_annotations = gc.get(f'/annotation?itemId={image_id}')
        for existing in existing_annotations:
            if existing['annotation'].get('name') == aggregated_ann_name:
                try:
                    gc.delete(f'/annotation/{existing["_id"]}')
                    print(f'Deleted previous annotation: {aggregated_ann_name} (id: {existing["_id"]})')
                except Exception as e:
                    print(f'Failed to delete previous {aggregated_ann_name}: {e}')

        gc.post(
            f'/annotation/item/{image_id}',
            data = json.dumps(formatted_anns),
            headers = {
                'X-HTTP-Method':'POST',
                'Content-Type': 'application/json'
            }
        )
        print(f'Uploaded annotation "{aggregated_ann_name}" under group "{aggregated_group}" to DSA')
    
if __name__=='__main__':
    main(CLIArgumentParser().parse_args())


