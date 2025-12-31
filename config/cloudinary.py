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

from . import env_is_test
from .settings import (
    DEBUG,
    CLOUDINARY_API_KEY, 
    CLOUDINARY_API_SECRET,
    ROUTINE_STALE_CLOUD_PUBID_DELETION,
    TEST_ROUTINE_STALE_CLOUD_PUBID_DELETION,
    CLOUDINARY_DELETION_LOCK_EXPIRY,
    TEST_CLOUDINARY_DELETION_LOCK_EXPIRY,
)

def routine_interval():
    return TEST_ROUTINE_STALE_CLOUD_PUBID_DELETION if env_is_test() else ROUTINE_STALE_CLOUD_PUBID_DELETION

cloudinary.config(
    cloud_name="dmjtks9zq",  
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)

def cloudinary_deletion_lock_expiry():
    return TEST_CLOUDINARY_DELETION_LOCK_EXPIRY if env_is_test() else CLOUDINARY_DELETION_LOCK_EXPIRY


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
