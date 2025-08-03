import psycopg2

# Database connection details
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

    # Step 1: Drop the 'client_type' column if it exists in the 'users' table
    drop_column_query = """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 
                       FROM information_schema.columns 
                       WHERE table_name='users' 
                         AND column_name='client_type') THEN
                ALTER TABLE users DROP COLUMN client_type;
            END IF;
        END $$;
    """
    cur.execute(drop_column_query)
    print("Column 'client_type' dropped from 'users' table if it existed.")

    # Step 2: Drop the 'client_type_choice' enum type if it exists
    drop_enum_query = """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'client_type_choice') THEN
                DROP TYPE client_type_choice;
            END IF;
        END $$;
    """
    cur.execute(drop_enum_query)
    print("Enum type 'client_type_choice' dropped if it existed.")

except Exception as e:
    print(f"Error: {e}")

finally:
    # Close the cursor and connection
    if cur:
        cur.close()
    if conn:
        conn.close()
