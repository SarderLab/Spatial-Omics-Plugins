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
    agg_annotations = [annotations[ann_names.index(i)] for i in args.agg_annotation.split(',') if i in ann_names]

    for ann in agg_annotations:
        agged_annotation = spatially_aggregate(ann,[base_annotation],separate=False,summarize=False)
        
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

        gc.post(
            f'/annotation/item/{image_id}',
            data = json.dumps(formatted_anns),
            headers = {
                'X-HTTP-Method':'POST',
                'Content-Type': 'application/json'
            }
        )


        print(f'Uploaded aggregated annotation: {ann["properties"]["name"]} to DSA')
    


if __name__=='__main__':
    main(CLIArgumentParser().parse_args())


