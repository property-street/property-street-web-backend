from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    Agent,
    Asset,
    AssetFeature,
)
from property_street_backend.clogs.logger_config import (
    log_message
)

async def get_agent_assets(db: AsyncSession, agent_id: int):
    """
    Function to return most assets published by an agent.
    It returns a dictionary of two entries:
    {
        assets_data: dict,
        grouped_cloud_details: dict,
    }
    1. The asset data.
    2. The linearized cloud image detail of each asset it fetched.
    """
    try:
        # Query the agent and related assets
        agent_query = await db.execute(
            select(Agent).filter(Agent.id == agent_id).options(
                selectinload(Agent.assets).selectinload(Asset.cover_image),
                selectinload(Agent.assets).selectinload(Asset.tags),
                selectinload(Agent.assets).selectinload(Asset.features).selectinload(AssetFeature.cloud_images),
                selectinload(Agent.assets).selectinload(Asset.cloud_images)
            )
        )
        agent = agent_query.scalars().first()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )

        assets_data = {}
        grouped_cloud_details = {}

        for asset_index, asset in enumerate(agent.assets):
            # Initialize sub-entry in grouped_cloud_details with index starting from 0
            grouped_cloud_details[asset_index] = {}
            sub_index = 0  # Reset sub-entry index for each asset

            # Prepare cover image structure
            cover_image_data = None
            if asset.cover_image:
                db_table_id = asset.cover_image.id
                cover_image_cloud_details = {
                    "cloud_asset_id": asset.cover_image.cloud_asset_id,
                    "format": asset.cover_image.format,
                    "bytes": asset.cover_image.bytes,
                    "height": asset.cover_image.height,
                    "public_id": asset.cover_image.public_id,
                    "secure_url": asset.cover_image.secure_url,
                    "width": asset.cover_image.width,

                    "db_table_id": db_table_id
                }
                cover_image_data = {
                    0:{
                        "files": {
                            asset.public_id : cover_image_cloud_details
                        }
                    }
                }

                # Add to grouped_cloud_details
                grouped_cloud_details[asset_index][sub_index] = {
                    'db_table_name': 'CloudImageDetail',
                    'cloud_details': cover_image_cloud_details
                }
                sub_index += 1  # Increment sub-entry index

            # Prepare tags structure
            tags_data = [{"db_table_id": tag.id, "name": tag.name} for tag in asset.tags]

            # Prepare features or no_features structure
            features_data = {}
            no_feature_data = {0: {'files': {}}}

            if asset.has_features:
                for i, feature in enumerate(asset.features):
                    feature_cloud_details = {}
                    for asset_cloud_image in feature.cloud_images:
                        cloud_image = {
                            "cloud_asset_id": asset_cloud_image.cloud_asset_id,
                            "format": asset_cloud_image.format,
                            "bytes": asset_cloud_image.bytes,
                            "height": asset_cloud_image.height,
                            "public_id": asset_cloud_image.public_id,
                            "secure_url": asset_cloud_image.secure_url,
                            "width": asset_cloud_image.width,
                            "db_table_id": asset_cloud_image.id
                        }
                        feature_cloud_details[asset_cloud_image.public_id] = cloud_image

                        # Add to grouped_cloud_details
                        grouped_cloud_details[asset_index][sub_index] = {
                            'db_table_name': 'AssetCloudImage',
                            'db_table_id': asset_cloud_image.id,
                            'cloud_details': cloud_image
                        }
                        sub_index += 1  # Increment sub-entry index

                    features_data[i] = {
                        "db_table_id": feature.id,
                        "title": feature.title,
                        "files": feature_cloud_details
                    }

            else:
                for i, asset_cloud_image in enumerate(asset.cloud_images):
                    cloud_image_obj = {
                        "cloud_asset_id": asset_cloud_image.cloud_asset_id,
                        "format": asset_cloud_image.format,
                        "bytes": asset_cloud_image.bytes,
                        "height": asset_cloud_image.height,
                        "public_id": asset_cloud_image.public_id,
                        "secure_url": asset_cloud_image.secure_url,
                        "width": asset_cloud_image.width,
                        "db_table_id": asset_cloud_image.id
                    }
                    no_feature_data[0]['files'][asset_cloud_image.public_id] = cloud_image_obj

                    # Add to grouped_cloud_details
                    grouped_cloud_details[asset_index][sub_index] = {
                        'db_table_name': 'AssetCloudImage',
                        'db_table_id': asset_cloud_image.id,
                        'cloud_details': cloud_image_obj
                    }
                    sub_index += 1  # Increment sub-entry index

            # Prepare asset structure
            asset_data = {
                "asset_id": asset.id,
                "category": asset.category,
                "title": asset.title,
                "cover_image": cover_image_data,
                "country": asset.country,
                "address": asset.address,
                "feature": features_data if asset.has_features else None,
                "no_feature": no_feature_data if not asset.has_features else None,
                "currency": asset.currency,
                "amount": asset.amount,
                "status": asset.status,
                "tags": tags_data,
                "lease_duration": asset.lease_duration,
                "description": asset.description,

                
            }

            # Add asset data to the collection
            assets_data[asset_index] = asset_data

        # log the success
        log_message(
            'success',
            f'Assets of agent {agent_id} successfully fetched'
        )

        return {
            "assets_data": assets_data,
            "grouped_cloud_details": grouped_cloud_details,
        }

    except Exception as e:
        # log the error
        log_message(
            'error',
            f'Retrieval of agent:{agent_id} assets failed. Reason: {e}'
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving agent's assets: {str(e)}"
        )
