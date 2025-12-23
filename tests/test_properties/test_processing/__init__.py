import time
from tests.activity.test_controller.test_objects import (
    area_template,
    tags_template,
    asset_data_template,
    cloud_image_template,
)

# test utility functions
def property_payload(agent_id, with_feature: bool = True):
    payload = {
        **asset_data_template,
        "agent_id": agent_id,
        "area" : {**area_template},
        "cover_image": {
            **cloud_image_template,
            'public_id':  f'covr_img_pub_id_{time.time()}'
        },
        "tags": [*tags_template],
    }

    if with_feature:
        payload["features"] = [{
            "title": f"Feature{i}",
            "cloud_images": [
                {
                    **cloud_image_template,
                    'public_id':  f'feat_img_{i}{j}_{time.time()}'
                } for j in range(2)
            ]
        } for i in range(2)]
        payload['features'].append({"title": "Car park"})
    else:
        payload["unfeatured_images"] = [
            {**cloud_image_template,
             'public_id':  f'unfeat_public_id_{time.time()}'}
        ]
    return payload