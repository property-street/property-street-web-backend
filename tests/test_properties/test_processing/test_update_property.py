import pytest
from httpx import AsyncClient
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    Asset,
    AssetFeature,
)
from .test_apply_model import create_test_asset
from tests.auth.test_create_agent import create_test_agent
from tests.activity.test_controller.test_objects import (
    cloud_image_template,
)
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.assets.schemas import PatchPropertySchema


@pytest.mark.asyncio
async def test_update_property(ignore_cloud_image_del, client__fixture: dict):
    # Get the yielded client object
    client: AsyncClient = client__fixture['http_client']
    test_db: AsyncSession = client__fixture['db']


    test_agent = await create_test_agent(test_db)
    created_property: Asset = await create_test_asset(
        test_db, test_agent.id
    )
    assert created_property
    prop_id = created_property.id

    # Retrieve some existing details
    
    #=======================
    # Process tag
    #=======================
    new_covr_img_public_id = 'new_covr_img_public_id'
    condo_tag_id: int = None
    tag_name_to_remove = "condo"
    tag_name_to_add = "1 bed"
    for tag in created_property.tags:
        if tag.name == tag_name_to_remove:
            condo_tag_id = tag.id
    assert condo_tag_id

    #=======================
    # Process features
    #=======================
    feat_0_id: int = (await test_db.execute(
        select(AssetFeature)
        .where(AssetFeature.asset_id == prop_id, 
            AssetFeature.title == "Feature0")
    )).scalar_one_or_none().id
    assert feat_0_id
    feat_1: Asset = (await test_db.execute(
        select(AssetFeature)
        .where(AssetFeature.asset_id == prop_id,
            AssetFeature.title == "Feature1")
    )).scalar_one_or_none()
    assert feat_1
    feat_1_id = feat_1.id
    feat_1_cld_img1_id = feat_1.cloud_images[0].id
    new_feat_1_cld_img1_pub_id = "new_feat_1_cld_img1_pub_id"
    new_feat_3_cld_img_pub_id = "new_feat_2_cld_img_pub_id"

    flat_fields = {
        "status": "Lease",
        "price": 500000,
        "category": "Peng house",
        "lease_duration": None,
    }
    payload = {
        **flat_fields,
        "id": prop_id,
        "tags": [
            { # test new addition
                "name": "1 bed" },
            { # test deletion
                "id": condo_tag_id, "action": "delete"},
        ],
        "cover_image": { # test replacement
            **cloud_image_template,
            'public_id': new_covr_img_public_id
        },
        "features": [{ # test deletion
            "action": "delete",
            "id": feat_0_id,
        },{
            "id": feat_1_id,
            "title": "Feature1",
            "cloud_images": [{ # test deletion
                "id": feat_1_cld_img1_id,
                "action": "delete",
            },{ # test new addition
                **cloud_image_template,
                "public_id": new_feat_1_cld_img1_pub_id
            }]
        },{ # test new addition (new feature)
            "title": "Feature3",
            "cloud_images": [{
                **cloud_image_template,
                "public_id": new_feat_3_cld_img_pub_id
            }]
        }]
    }
    PatchPropertySchema.model_validate(payload)
    

    # fetch a token for the user
    token = fetch_access_token(user=test_agent)['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.patch(
        f"/assets/{prop_id}",
        json=payload,  # Use json instead of data for a JSON body
        headers=headers
    )
    assert response.status_code == 200
    property = response.json()
    # flat fields assertions
    assert all(
        property[field] == payload[field] for field in list(flat_fields.keys())
    ) 
    # tag assertions
    tags = property['tags']
    assert all(
        (   
            ("id" in tag and "name" in tag)
            and (
                (tag['name'] == tag_name_to_add) 
                or (tag['name'] != tag_name_to_remove)
            )
        ) 
        for tag in tags
    )
    # cover image assertions
    assert property['cover_image']['public_id'] == new_covr_img_public_id

    # features assertions
    features = property['features']
    # Feature0 should be deleted
    assert all(f['id'] != feat_0_id for f in features)

    # Feature1 should still exist and not include the old cloud image id, but include the new public id
    feat1 = next((f for f in features if f.get('id') == feat_1_id), None)
    assert feat1 is not None
    assert all(ci['id'] != feat_1_cld_img1_id for ci in feat1.get('cloud_images', []))
    assert any(ci['public_id'] == new_feat_1_cld_img1_pub_id for ci in feat1.get('cloud_images', []))

    # New Feature2 should be present with its cloud image
    feat3 = next((f for f in features if f.get('title') == 'Feature3'), None)
    assert feat3 is not None
    assert any(ci['public_id'] == new_feat_3_cld_img_pub_id for ci in feat3.get('cloud_images', []))

    #====================================================================================
    # Now, change the property from featured -> unfeatured
    #====================================================================================
    new_unfeat_pub_id = 'new_unfeat_img_pub_id'
    payload_unfeatured = {
        "id": prop_id,
        "features": [
            {"id": obj['id'], "action":"delete"}
            for obj in property['features']
        ],
        "unfeatured_images": [{**cloud_image_template, "public_id": new_unfeat_pub_id}]
    }
    response = await client.patch(
        f"/assets/{prop_id}",
        json=payload_unfeatured,
        headers=headers
    )
    assert response.status_code == 200
    property_unfeat = response.json()
    assert not property_unfeat.get('has_features')
    assert not property_unfeat.get('features')
    assert any(ci['public_id'] == new_unfeat_pub_id for ci in property_unfeat.get('unfeatured_images', []))