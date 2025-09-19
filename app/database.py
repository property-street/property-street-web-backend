from property_street_backend.config.postgres_connection_manager import get_postgres_instance


# Dependency to get async DB session
async def get_db():
    async with get_postgres_instance() as db:
        yield db