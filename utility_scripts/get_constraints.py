import asyncpg
import asyncio

# Database connection details
db_name = 'property_street_store'
user = 'postgres'
password = 'postgres'
host = 'localhost'
port = '5432'  # Default PostgreSQL port

async def get_constraints():
    # Connect to your PostgreSQL database
    conn = await asyncpg.connect(
        user=user,
        password=password,
        database=db_name,
        host=host
    )
    
    # Define the query to fetch foreign key constraints
    query = """
    SELECT
        conname AS constraint_name,
        conrelid::regclass AS table_name,
        confrelid::regclass AS referenced_table
    FROM
        pg_constraint
    WHERE
        confrelid = 'assets'::regclass;
    """
    
    # Execute the query
    results = await conn.fetch(query)
    
    # Print the results
    for record in results:
        print(f"Constraint: {record['constraint_name']}, "
              f"Table: {record['table_name']}, "
              f"Referenced Table: {record['referenced_table']}")
    
    # Close the connection
    await conn.close()

# Run the async function
asyncio.run(get_constraints())
