# test_cloudinary_delete.py
import uuid
import pytest
import cloudinary.api

from property_street_backend.config.cloudinary import upload_image, delete_image


@pytest.mark.integration
def test_cloudinary_upload_and_delete():
    # --- Arrange ---
    test_image_path = "tests/test_cloudinary/test.jpg"
    public_id = f"pytest/{uuid.uuid4()}"

    # --- Upload ---
    upload_response = upload_image(test_image_path, public_id)

    assert upload_response["public_id"] == public_id
    assert upload_response["secure_url"].startswith("https://")

    # --- Ensure asset exists ---
    resource = cloudinary.api.resource(public_id)
    assert resource["public_id"] == public_id
    

    # --- Delete ---
    delete_response = delete_image(public_id)
    assert delete_response["result"] == "ok"

    # --- Verify deletion ---
    with pytest.raises(cloudinary.api.NotFound):
        cloudinary.api.resource(public_id)
