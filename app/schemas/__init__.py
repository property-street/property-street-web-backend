from pydantic import BaseModel, ConfigDict, create_model
from typing import Optional, get_origin, get_args, Union, Literal

class ConfigDictSetter(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class UtilitySchemaMixin:
    action: Optional[Literal["delete"]] = None

UtilitySchema = UtilitySchemaMixin

def make_optional(model: type[BaseModel], FIELDS_TO_SKIP: set = None) -> type[BaseModel]:
    optional_fields = {}

    for name, field in model.model_fields.items():
        if FIELDS_TO_SKIP and name in FIELDS_TO_SKIP:
            continue   # <-- prevent shadowing
        
        annotation = field.annotation

        # Skip nested models & collections
        if get_origin(annotation) in (list, dict, tuple, set):
            optional_fields[name] = (annotation, field.default)
            continue

        # Already optional
        if get_origin(annotation) is Union and type(None) in get_args(annotation):
            optional_fields[name] = (annotation, field.default)
            continue

        # Make direct primitive optional
        optional_fields[name] = (Optional[annotation], None)

    Partial = create_model(
        f"{model.__name__}Patch",
        __base__=model,
        **optional_fields
    )

    return Partial

def make_optional_deep(model: type[BaseModel], cache=None) -> type[BaseModel]:
    if cache is None:
        cache = {}

    if model in cache:
        return cache[model]

    fields = {}

    for name, field in model.model_fields.items():
        type_hint = field.annotation

        # Nested BaseModel → transform recursively
        if isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
            type_hint = make_optional_deep(type_hint, cache)

        # Lists of models
        elif get_origin(type_hint) is list:
            (inner,) = get_args(type_hint)
            if isinstance(inner, type) and issubclass(inner, BaseModel):
                inner = make_optional_deep(inner, cache)
            type_hint = Optional[list[inner]]

        # Wrap non-optional field
        if get_origin(type_hint) is not Union or type(None) not in get_args(type_hint):
            type_hint = Optional[type_hint]

        fields[name] = (type_hint, None)

    partial_cls = create_model(f"{model.__name__}Partial", __base__=model, **fields)
    cache[model] = partial_cls
    return partial_cls

# make_optional = make_optional_deep