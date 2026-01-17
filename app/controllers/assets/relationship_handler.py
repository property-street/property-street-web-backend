from sqlalchemy.future import select
from sqlalchemy.inspection import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import RelationshipProperty
from property_street_backend.app.initiator import logger
from typing import Dict, Any, Callable, Optional, Union, Awaitable

def normalize_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures consistency: convert nested dicts, primitives, lists, relationships."""
    normalized = {}

    for key, value in data.items():
        if isinstance(value, dict):
            # Detect relationship vs direct struct
            if "id" in value or any(k.endswith("_id") for k in value.keys()):
                normalized[key] = {"__rel__": True, **value}
            else:
                normalized[key] = normalize_payload(value)

        elif isinstance(value, list):
            normalized[key] = [
                normalize_payload(v) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            normalized[key] = value

    return normalized


class ORMTransformer:
    def __init__(self, model_cls, db: AsyncSession):
        self.model = model_cls
        self.db = db
        self.mapper = inspect(model_cls)

    def is_column(self, field: str) -> bool:
        return field in self.mapper.columns

    def is_relationship(self, field: str) -> bool:
        return field in self.mapper.relationships

    def rel_type(self, field: str) -> str:
        rel = self.mapper.relationships[field]
        rel_prop: RelationshipProperty = rel
        if rel_prop.uselist is False:
            if rel_prop.direction.name == 'MANYTOONE': 
                rel_type = 'many_to_one' 
            else: 
                rel_type = 'one_to_one'
        else:
            if rel_prop.direction.name == 'MANYTOONE': 
                rel_type = 'one_to_many' # Reverse relationship 
            else: 
                rel_type = 'many_to_many'
        return rel_type

    def related_model(self, field: str):
        return self.mapper.relationships[field].mapper.class_


class RelationshipExecutor:
    def __init__(self, db: AsyncSession):
        self.db = db

    def can_delete(self, data: dict) -> bool:
        return data.get("action") == "delete"

    async def rmv_frm_parent(self, *, instance, rel_type, parent=None, rel_name=None):
        # MANY-TO-MANY → unlink only
        if rel_type == "many_to_many":
            if not(parent and rel_name):
                raise ValueError("parent and rel_name must be provided for a many-to-many relationship.")
            collection = getattr(parent, rel_name)
            if instance in collection:
                collection.remove(instance)
            return True

        # ONE-TO-MANY or ONE-TO-ONE → hard delete
        if rel_type in ("one_to_many", "one_to_one"):
            await self.db.delete(instance)
            return True

        # MANY-TO-ONE → null FK if nullable, else delete
        if rel_type == "many_to_one":
            mapper = inspect(instance.__class__)
            # better FK detection:
            fk_col = next((c for c in mapper.columns if c.foreign_keys), None)

            if fk_col and fk_col.nullable:
                setattr(instance, fk_col.name, None)
            else:
                await self.db.delete(instance)
            return True

        return False


    async def apply(self, instance, normalized_data: dict):
        transformer = ORMTransformer(instance.__class__, self.db)

        for field, value in normalized_data.items():

            # 1️⃣ Plain column
            if transformer.is_column(field):
                setattr(instance, field, value)
                continue

            # 2️⃣ Relationship
            if transformer.is_relationship(field):
                related_cls = transformer.related_model(field)
                rel_type = transformer.rel_type(field)


                # branching correctly
                if rel_type.endswith("_many"):
                    await self._handle_many(instance, field, value, related_cls, rel_type)
                else:
                    await self._handle_one(instance, field, value, related_cls, rel_type)

        self.db.add(instance)
        return instance


    async def _handle_one(self, instance, field, value, related_cls, rel_type):
        # Perform deletion first if flagged
        if self.can_delete(value):
            target = await self.db.get(related_cls, value["id"])
            await self.rmv_frm_parent(
                instance=target,
                data=value,
                rel_type=rel_type,
                parent=instance,
                rel_name=field
            )
            return
        
        if value is None:
            setattr(instance, field, None)
            return

        if isinstance(value, dict) and "id" in value:
            obj = await self.db.get(related_cls, value["id"])
            
            if self.can_delete(value): # Handle deletion
                await self.rmv_frm_parent(instance=obj,rel_type=rel_type)
            else:
                await self.apply(obj, value)
        else:
            obj = related_cls()
            await self.apply(obj, value)

        setattr(instance, field, obj)


    async def _handle_many(self, instance, field, items, related_cls, rel_type):
        """
        Handle a many relationship (one-to-many or many-to-many) with merge semantics.

        - Updates existing items by ID or unique constraint
        - Creates new items if no match
        - Preserves existing items not referenced in the payload
        """
        existing_list = getattr(instance, field)
        existing_by_id = {obj.id: obj for obj in existing_list if hasattr(obj, "id")}

        # Collect objects that will be kept after merge
        merged_list = []

        for item in items:
            # Case 1 → Update via explicit ID
            if isinstance(item, dict) and "id" in item:
                obj = existing_by_id.get(item["id"]) or await self.db.get(related_cls, item["id"])
                if self.can_delete(item): # Handle deletion
                    await self.rmv_frm_parent(
                        instance=obj,
                        rel_type=rel_type,
                        parent=instance,
                        rel_name=field
                    )
                    continue
                else:
                    await self.apply(obj, item)

            else:
                # Case 2 → Attempt to match unique constraints (name, email, slug, etc.)
                obj = await self._find_existing_match(related_cls, item)

                # Case 3 → No match → create new instance
                if not obj:
                    obj = related_cls()

                await self.apply(obj, item)

            merged_list.append(obj)

        # Merge: keep existing items not referenced in the payload
        for existing_obj in existing_list:
            if existing_obj not in merged_list:
                merged_list.append(existing_obj)

        setattr(instance, field, merged_list)

        # Replace semantics (diff mode)
        # existing_list.clear()
        # existing_list.extend(new_list)

    
    async def _find_existing_match(self, related_cls, payload: dict):
        """Try to find an existing row based on any unique column present in payload."""
        mapper = inspect(related_cls)

        # Get unique columns (including primary key, unique=True, and unique indexes)
        unique_columns = [
            col for col in mapper.columns
            if col.primary_key or col.unique
        ]

        if not unique_columns:
            return None  # no unique identifiers → cannot resolve safely

        # Try matching the first unique field found in input
        filters = []
        for col in unique_columns:
            if col.name in payload and payload[col.name] is not None:
                filters.append(col == payload[col.name])

        if not filters:
            return None

        stmt = select(related_cls).where(*filters)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

ExtraHook = Union[
    Callable[[Any], None],
    Callable[[Any], Awaitable[None]],
]

async def apply_model(model_cls, db: AsyncSession, data: dict, instance=None, extra_before_commit: Optional[ExtraHook] = None):
    normalized = normalize_payload(data)

    if instance is None:
        instance = model_cls()

    executor = RelationshipExecutor(db)
    await executor.apply(instance, normalized)

    if extra_before_commit:
        result = extra_before_commit(instance)
        if hasattr(result, "__await__"):
            await result


    await db.flush()
    await db.commit()
    await db.refresh(instance)

    return instance