# test_cloudinary_delete.py
import pytest
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models_helper import CloudImageDetail
from property_street_backend.app.controllers.cloudinary.models import CloudDeletionOutbox
from property_street_backend.tests.activity.test_controller.test_objects import cloud_image_template

@pytest.mark.asyncio
async def test_public_id_changes_outbox_persistence(client__fixture):
    test_db: AsyncSession = client__fixture['db']

    #==============================
    # Test for deletion
    #==============================
    inst = CloudImageDetail(**cloud_image_template)
    test_db.add(inst)
    await test_db.commit()
    await test_db.refresh(inst)
    # delete instance
    await test_db.delete(inst)
    await test_db.commit()
    # assert outbox
    inst_to_del = (await test_db.execute(
        select(CloudDeletionOutbox)
        .where(CloudDeletionOutbox.public_id == inst.public_id)
    )).scalars().first()
    if not inst_to_del:
        raise Exception("**Instance for deletion not found in async session!")
    await test_db.delete(inst_to_del)
    await test_db.commit()


    #==============================
    # Test for modification
    #==============================
    old_public_id = cloud_image_template["public_id"]
    new_public_id = old_public_id + 'b'
    inst = CloudImageDetail(**cloud_image_template)
    test_db.add(inst)
    await test_db.commit()
    await test_db.refresh(inst)
    # modify public id
    inst.public_id = new_public_id
    test_db.add(inst)
    await test_db.commit()
    # assert outbox
    inst_to_del = (await test_db.execute(
        select(CloudDeletionOutbox)
        .where(CloudDeletionOutbox.public_id == old_public_id)
    )).scalars().first()
    if not inst_to_del:
        raise Exception("**Instance for deletion not found!")
