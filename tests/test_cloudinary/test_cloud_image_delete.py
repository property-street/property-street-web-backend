# test_cloudinary_delete.py
import pytest
import cloudinary.api
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.tests.activity.test_controller.test_objects import cloud_image_template
from property_street_backend.app.models_helper import CloudImageDetail
from property_street_backend.config.cloudinary import upload_image, delete_image
from property_street_backend.app.schemas.cloud_image_schema import CloudImageSchema


@pytest.mark.asyncio
async def test_cloud_image_delete(client__fixture):
    test_db: AsyncSession = client__fixture['db']

    # --- Arrange ---
    test_image_path = "tests/test_cloudinary/test.jpg"
    public_id = f"pytest/test-public-id"
    
    try:    
        # --- Upload ---
        upload_response = upload_image(test_image_path, public_id)

        assert upload_response["public_id"] == public_id
        assert upload_response["secure_url"].startswith("https://")

        # --- Ensure asset exists ---
        resource = cloudinary.api.resource(public_id)
        assert resource["public_id"] == public_id

        #==============================
        # Create model with details
        #==============================
        upload_response["cloud_asset_id"] = upload_response["asset_id"]
        data = CloudImageSchema(**upload_response).model_validate().model_dump()
        inst = CloudImageDetail(**data)
        test_db.add(inst)
        await test_db.commit()
        await test_db.refresh(inst)

        #==============================
        # Delete model
        #==============================
        await test_db.delete(inst)
        await test_db.commit()
    finally:
        # --- Verify deletion ---
        try:
            cloudinary.api.resource(public_id)
            delete_response = delete_image(public_id)
            assert delete_response["result"] == "ok"
            raise cloudinary.api.AlreadyExists
        except cloudinary.api.NotFound:
            return
