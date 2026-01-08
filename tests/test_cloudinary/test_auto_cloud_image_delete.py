# test_cloudinary_delete.py
import pytest
import asyncio
import cloudinary.api
from sqlalchemy import text
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.initiator import logger
from property_street_backend.app.models_helper import CloudImageDetail
from property_street_backend.config.cloudinary import upload_image, delete_image
from property_street_backend.app.schemas.cloud_image_schema import CloudImageSchema
from property_street_backend.app.controllers.cloudinary.models import CloudDeletionOutbox
from property_street_backend.config.postgres_connection_manager import runtime_sync_session_maker
from property_street_backend.tests.activity.test_controller.test_objects import cloud_image_template
from property_street_backend.config.cloudinary import routine_interval as cloudinary_routine_interval


async def create_cloud_image_persist_to_db(test_db: AsyncSession, public_id):
    # --- Arrange ---
    test_image_path = "tests/test_cloudinary/test.jpg"
    
    # --- Upload ---
    upload_response: dict = upload_image(test_image_path, public_id)

    assert upload_response["public_id"] == public_id
    assert upload_response["secure_url"].startswith("https://")

    # --- Ensure asset exists ---
    resource = cloudinary.api.resource(public_id)
    assert resource["public_id"] == public_id

    #==============================
    # Create model with details
    #==============================
    cloud_image_template['public_id'] = public_id
    data = CloudImageSchema.model_validate(cloud_image_template).model_dump()
    inst = CloudImageDetail(**data)
    test_db.add(inst)
    await test_db.commit()
    await test_db.refresh(inst)
    return inst

async def confirm_outbox_wait_deletion(test_db: AsyncSession, public_id):
    # Ensure persistence in the cloud deletion outbox
    inst_to_del = (await test_db.execute(
        select(CloudDeletionOutbox)
        .where(CloudDeletionOutbox.public_id == public_id)
    )).scalars().first()
    if not inst_to_del:
        raise Exception("**Instance for deletion not found in async session!")

    # Ensure persistence in the cloud deletion outbox
    SessionLocal = runtime_sync_session_maker()
    with SessionLocal() as session:
        inst_to_del = (session.execute(
            select(CloudDeletionOutbox)
            .where(CloudDeletionOutbox.public_id == public_id)
        )).scalars().first()
        if not inst_to_del:
            raise Exception("**Instance for deletion not found in sync session!")

    await asyncio.sleep(cloudinary_routine_interval()+10)

def run_finally(public_id):       
    try:
        cloudinary.api.resource(public_id)
        delete_response = delete_image(public_id)
        assert delete_response["result"] == "ok"
        raise cloudinary.api.AlreadyExists
    except cloudinary.api.NotFound:
        pass


@pytest.mark.asyncio
async def test_cloud_image_delete(celery_worker_and_beat, client__fixture):
    test_db: AsyncSession = client__fixture['db']
    public_id = f"pytest/test-public-id"

    #=================================
    # Create model and delete instance
    #=================================
    try:
        inst = await create_cloud_image_persist_to_db(test_db, public_id)
        await test_db.delete(inst)
        await test_db.commit()
        # Ensure persistence in the cloud deletion outbox and task deletion
        await confirm_outbox_wait_deletion(test_db, public_id)
    finally:
        run_finally(public_id)

    #==============================================
    # Create model and modify public id of instance
    #==============================================
    try:
        inst = await create_cloud_image_persist_to_db(test_db, public_id)
        new_public_id = public_id + 'b'
        inst.public_id = new_public_id
        test_db.add(inst)
        await test_db.commit()
        # Ensure persistence in the cloud deletion outbox and task deletion
        await confirm_outbox_wait_deletion(test_db, public_id)
    finally:
        run_finally(public_id)