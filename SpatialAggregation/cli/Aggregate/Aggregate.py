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


def main(args):

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
        # Save original name for deletion BEFORE any modifications
        original_ann_name = ann['properties']['name']

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
            
            # Extract Condition from Condition_Aggregated (NEW CODE)
            if "user" in el:
                condition_data = el["user"].get("Condition_Aggregated", {}).get("Count", {})
                if condition_data:
                    # Extract the first key (e.g., "AKI")
                    condition = list(condition_data.keys())[0]
                    # Add it as a simple string field
                    el["user"]["Condition"] = condition

        # Delete ALL existing annotations with the ORIGINAL name before uploading
        ann_name = ann['properties']['name']  # This is the modified name (for upload)
        existing_annotations = gc.get(f'/annotation?itemId={image_id}')
        print(f'Found {len(existing_annotations)} existing annotations for this item')
        for existing in existing_annotations:
            existing_name = existing['annotation'].get('name')
            # Use original_ann_name for deletion (e.g., "arteries/arterioles")
            if existing_name == original_ann_name:
                try:
                    gc.delete(f'/annotation/{existing["_id"]}')
                    print(f'Deleted existing annotation: {original_ann_name} (id: {existing["_id"]})')
                except Exception as e:
                    print(f'Failed to delete annotation {original_ann_name}: {e}')

        gc.post(
            f'/annotation/item/{image_id}',
            data = json.dumps(formatted_anns),
            headers = {
                'X-HTTP-Method':'POST',
                'Content-Type': 'application/json'
            }
        )
        print(f'Uploaded aggregated annotation: {ann_name} to DSA')
    
if __name__=='__main__':
    main(CLIArgumentParser().parse_args())


