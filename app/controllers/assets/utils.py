from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from property_street_backend.app.controllers.assets.models import Asset
from property_street_backend.app.controllers.actors.models import User

def eager_asset_load():
    return (
        select(Asset)
        .options(
            selectinload(Asset.features),
            selectinload(Asset.tags),
            selectinload(Asset.area),
            selectinload(Asset.unfeatured_images),
            selectinload(Asset.cover_image),
            selectinload(Asset.agent)
            .selectinload(User.profile_avatar)
        )
    )