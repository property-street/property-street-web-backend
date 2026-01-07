from alembic import op

def create_enum_if_not_exists(enum_name: str, values: list[str]) -> None:
    values_sql = ", ".join(f"'{v}'" for v in values)

    op.execute(f"""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_type WHERE typname = '{enum_name}'
        ) THEN
            CREATE TYPE {enum_name} AS ENUM ({values_sql});
        END IF;
    END
    $$;
    """)
    
def drop_enum_if_unused(enum_name: str) -> None:
    op.execute(f"""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_attribute a
            JOIN pg_type t ON a.atttypid = t.oid
            WHERE t.typname = '{enum_name}'
        ) THEN
            DROP TYPE {enum_name};
        END IF;
    END
    $$;
    """)