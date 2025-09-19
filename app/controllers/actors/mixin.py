from sqlalchemy.orm import validates

class UniqueIDArrayMixin:
    """Mixin to enforce set-like behavior on ARRAY(Integer) fields."""

    array_field_name: str = None  # subclass must override

    def add_id(self, value: int):
        current = set(getattr(self, self.array_field_name) or [])
        current.add(value)
        setattr(self, self.array_field_name, list(current))

    def remove_id(self, value: int):
        current = set(getattr(self, self.array_field_name) or [])
        if value in current:
            current.remove(value)
        setattr(self, self.array_field_name, list(current))

    @validates("cached_roomies_application_ids")  # 👈 you can generalize if needed
    def _ensure_unique(self, key, value):
        if value is None:
            return []
        return list(set(value))
