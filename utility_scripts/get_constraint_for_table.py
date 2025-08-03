import psycopg2

# Extracted connection details from the URL: postgresql+asyncpg://postgres:postgres@localhost/property_street_store
db_name = 'property_street_store'
user = 'postgres'
password = 'postgres'
host = 'localhost'
port = '5432'  # Default PostgreSQL port

try:
    # Connect to the PostgreSQL database using psycopg2
    conn = psycopg2.connect(
        dbname=db_name,
        user=user,
        password=password,
        host=host,
        port=port  # Optional if it's the default PostgreSQL port (5432)
    )
    conn.autocommit = True  # Enable autocommit mode
    cur = conn.cursor()

    # Execute the query to retrieve constraint names for the 'assets' table
    query = """
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'assets'::regclass;
    """
    cur.execute(query)

    # Fetch and display the results
    constraints = cur.fetchall()
    for constraint in constraints:
        print(constraint[0])  # Print each constraint name

except Exception as e:
    print(f"Error: {e}")

finally:
    # Close the cursor and connection
    if cur:
        cur.close()
    if conn:
        conn.close()
