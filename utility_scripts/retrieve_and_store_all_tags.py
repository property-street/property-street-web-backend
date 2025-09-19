import asyncio
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from property_street_backend.app.database import get_db
from property_street_backend.app.models import Tag, AddOn


async def populate_addon_tag_list(
    session: AsyncSession
):
    """
    Fetches all tags from the Tag table and updates the tag_list attribute
    for all AddOn entries, or creates a new one if none exist.
    """
    try:
        # Fetch all tags
        result = await session.execute(select(Tag.name))
        tags = [row[0] for row in result.fetchall()]  # List of tag names
        
        # Check if an AddOn entry exists; update or create
        addon = await session.execute(select(AddOn).limit(1))
        existing_addon = addon.scalars().first()
        
        if existing_addon:
            # Update the existing AddOn
            existing_addon.tag_list = tags
        else:
            # Create a new AddOn entry
            new_addon = AddOn(tag_list=tags)
            session.add(new_addon)

        await session.commit()
        print("AddOn tag_list updated successfully.")
        return True
    except Exception as e:
        print(f"Error occurred: {e}")
        return False


async def main():
    session = await get_db().__anext__()
    await populate_addon_tag_list(session=session)


if __name__ == "__main__":
    asyncio.run(main())
