"""de-nullification of area_id of Asset model

Revision ID: 97a7bdb29239
Revises: ac3dde323377
Create Date: 2026-01-05 17:19:17.317406

"""
from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union
from sqlalchemy.sql import select, insert


# revision identifiers, used by Alembic.
revision: str = '97a7bdb29239'
down_revision: Union[str, None] = 'ac3dde323377'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    meta = sa.MetaData()
    meta.bind = bind

    assets = sa.Table(
        "assets",
        meta,
        sa.Column("id", sa.Integer),
        sa.Column("area_id", sa.Integer),
    )

    areas = sa.Table(
        "areas",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("country", sa.String),
        sa.Column("state_or_province", sa.String),
        sa.Column("city_or_town", sa.String),
        sa.Column("county", sa.String),
        sa.Column("street", sa.String),
        sa.Column("zip_or_postal_code", sa.String),
        sa.Column("building_name_or_suite", sa.String),
    )

    # 1️⃣ Fetch assets with NULL area_id
    null_assets = bind.execute(
        select(assets.c.id).where(assets.c.area_id.is_(None))
    ).fetchall()

    for (asset_id,) in null_assets:
        # 2️⃣ Create a placeholder Area
        result = bind.execute(
            insert(areas).values(
                country="Canada",
                state_or_province="Ontario",
                city_or_town="Toronto",
                county=None,
                street="55 King Street West",
                zip_or_postal_code=None,
                building_name_or_suite=None,
            ).returning(areas.c.id)
        )

        area_id = result.scalar_one()

        # 3️⃣ Assign area_id to asset
        bind.execute(
            assets.update()
            .where(assets.c.id == asset_id)
            .values(area_id=area_id)
        )

    # 4️⃣ Enforce NOT NULL constraint
    op.alter_column(
        "assets",
        "area_id",
        existing_type=sa.INTEGER(),
        nullable=False,
    )


def downgrade() -> None:
    # Remove NOT NULL constraint
    op.alter_column(
        "assets",
        "area_id",
        existing_type=sa.INTEGER(),
        nullable=True,
    )
