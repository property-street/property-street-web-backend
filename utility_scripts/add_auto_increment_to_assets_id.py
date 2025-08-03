import asyncpg
import asyncio

# Database connection details
db_name = 'property_street_store'
user = 'postgres'
password = 'postgres'
host = 'localhost'
port = '5432'

async def configure_agents_id_autoincrement():
    # Connect to your PostgreSQL database
    conn = await asyncpg.connect(
        user=user,
        password=password,
        database=db_name,
        host=host,
        port=port
    )

    # Step 1: Create the sequence if it does not exist
    create_sequence_query = """
    CREATE SEQUENCE IF NOT EXISTS agents_id_seq;
    """
    await conn.execute(create_sequence_query)

    # Step 2: Alter the `id` column to use this sequence as the default
    alter_column_query = """
    ALTER TABLE agents ALTER COLUMN id SET DEFAULT nextval('agents_id_seq');
    """
    await conn.execute(alter_column_query)

    # Step 3: Set ownership of the sequence to the `id` column
    set_sequence_owner_query = """
    ALTER SEQUENCE agents_id_seq OWNED BY agents.id;
    """
    await conn.execute(set_sequence_owner_query)

    # Verification query: Check if the `id` column is using the auto-increment sequence
    verify_query = """
    SELECT column_default
    FROM information_schema.columns
    WHERE table_name = 'agents' AND column_name = 'id';
    """
    result = await conn.fetch(verify_query)
    column_default = result[0].get("column_default", None)

    # Print verification result
    if column_default and 'nextval' in column_default:
        print("The 'id' column in the 'agents' table is now set to auto-increment.")
    else:
        print("The 'id' column in the 'agents' table is NOT set to auto-increment.")

    # Close the connection
    await conn.close()

# Run the async function
asyncio.run(configure_agents_id_autoincrement())
