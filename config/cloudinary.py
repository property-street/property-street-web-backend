# ==============================
# Set your Cloudinary credentials
# ==============================
import os
from dotenv import load_dotenv
load_dotenv()

# Import the Cloudinary libraries
# ==============================
import cloudinary
from cloudinary.uploader import upload
from cloudinary.uploader import destroy

from .settings import CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

cloudinary.config(
    cloud_name="dmjtks9zq",  
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)

def upload_image(file_path: str, public_id: str):
    response = upload(
        file_path,
        public_id=public_id,
        resource_type="image",
        overwrite=True,
        upload_preset="ml_default",  # or your preset
    )
    return response

def ignore_cloudinary_deletion():
    TEST_CLOUD_IMAGE_DEL = os.getenv("TEST_CLOUD_IMAGE_DEL")
    return TEST_CLOUD_IMAGE_DEL is not None

def delete_image(public_id: str):
    if ignore_cloudinary_deletion():
        return
    return destroy(
        public_id,
        resource_type="image",
        invalidate=True,
    )