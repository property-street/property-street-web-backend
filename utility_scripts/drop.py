import asyncpg
import asyncio

# Database connection details
default_db = 'postgres'  # Default database for administrative tasks
user = 'postgres'
password = 'postgres'
host = 'localhost'
port = '5432'  # Default PostgreSQL port
db_to_be_dropped = 'property_street_store'


async def drop_database():
    conn = await asyncpg.connect(
        user=user,
        password=password,
        database=default_db,
        host=host
    )
    # Terminate connections before dropping the database
    await conn.execute(f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{db_to_be_dropped}'
          AND pid <> pg_backend_pid();
    """)
    
    # Drop the database
    await conn.execute(f'DROP DATABASE IF EXISTS {db_to_be_dropped};')
    print(f"{db_to_be_dropped} dropped successfully.")
    await conn.close()

# Run the async function
asyncio.run(drop_database())
