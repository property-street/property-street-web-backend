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

    # Execute the query to drop the enum type if it exists
    query = """
        DROP TYPE IF EXISTS email_management_reason_choice CASCADE;
    """
    cur.execute(query)

    print("Enum type 'email_management_reason_choice' has been deleted (if it existed).")

except Exception as e:
    print(f"Error: {e}")

finally:
    # Close the cursor and connection
    if cur:
        cur.close()
    if conn:
        conn.close()
