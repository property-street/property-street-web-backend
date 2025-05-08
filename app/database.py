from property_street_backend.config.context_sessions import get_db_based_on_context


# Dependency to get async DB session
async def get_db():
    async for db in get_db_based_on_context():
        yield db
