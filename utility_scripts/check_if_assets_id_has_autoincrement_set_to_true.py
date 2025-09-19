import asyncpg
import asyncio

# Database connection details
db_name = 'property_street_store'
user = 'postgres'
password = 'postgres'
host = 'localhost'
port = '5432'  # Default PostgreSQL port

async def check_agents_id_auto_increment():
    # Connect to your PostgreSQL database
    conn = await asyncpg.connect(
        user=user,
        password=password,
        database=db_name,
        host=host
    )
    
    # Define the query to check if the `id` column in the `agents` table is set to auto-increment
    query = """
    SELECT column_default
    FROM information_schema.columns
    WHERE table_name = 'agents' AND column_name = 'id';
    """
    
    # Execute the query
    result = await conn.fetch(query)
    
    # Check and interpret the result
    if result:
        column_default = result[0]['column_default']
        if column_default and 'nextval' in column_default:
            print("The 'id' column in the 'agents' table is set to auto-increment.")
        else:
            print("The 'id' column in the 'agents' table is NOT set to auto-increment.")
    else:
        print("The 'agents' table or the 'id' column does not exist.")
    
    # Close the connection
    await conn.close()

# Run the async function
asyncio.run(check_agents_id_auto_increment())
