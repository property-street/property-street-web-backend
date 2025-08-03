import argparse
import psycopg2
from psycopg2 import sql

def create_database(db_name, host, user, password):
    # Connect to the PostgreSQL server
    try:
        conn = psycopg2.connect(
            dbname='postgres',  # Default database
            user=user,
            password=password,
            host=host
        )
        conn.autocommit = True  # Enable autocommit mode
        cur = conn.cursor()

        # Create the new database
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))

        print(f"Database '{db_name}' created successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Create a PostgreSQL database.")
    parser.add_argument('db_name', type=str, help='Name of the database to create')
    parser.add_argument('--host', type=str, default='localhost', help='Database host (default: localhost)')
    parser.add_argument('--user', type=str, default='postgres', help='Database user (default: postgres)')
    parser.add_argument('--password', type=str, default='postgres', help='Database password (default: postgres)')

    args = parser.parse_args()

    # Call the function with command-line arguments
    create_database(args.db_name, args.host, args.user, args.password)

# python create_new_db.py property_street_store --host localhost --user postgres --password postgres
# Here, my_database is the name of the database you want to create.    

# i.e
# postgresql+asyncpg://<username>:<password>@<hostname>:<port>/<database_name>
# postgresql+asyncpg: Specifies the database type and the driver (e.g., asyncpg is the asynchronous PostgreSQL driver, commonly used with asyncpg and FastAPI).
# <username>: The database username.
# <password>: The password associated with the database username.
# <hostname>: The host where the PostgreSQL database is running (e.g., db if running inside Docker, or localhost if running locally).
# <port>: The port the database is running on (the default PostgreSQL port is 5432).
# <database_name>: The name of the specific database you want to connect to.