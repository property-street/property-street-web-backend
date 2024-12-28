# Property Street Backend


## Starting the development server
```
uvicorn app.main:app --reload
```

## Starting the redis server
```
sudo service redis-server start
```

## Running tests
pytest path_to_test_script


## activate the fast api shell
```
    ipython -i scripts/ipython_config.py
``` 


## Configure alembic.ini and env.py for your database

### initialize alembic
```
alembic init alembic
```

### Generate a new migration
```
alembic revision --autogenerate -m "Creation of the EmailManagementModel model"
```
##### Apply migration.
```
alembic upgrade head
```

### Downgrade Database: 
#### Revert to a previous migration (replace -1 with the number of steps to go back):
```
alembic downgrade -1
```

### Check Current Revision: 
#### See the current version of the database:
```
alembic current
```

### Show History of Revisions: 
#### List all migration scripts:
```
alembic history
```

## Generate SQL Scripts for Migrations
```
alembic upgrade <revision_or_head> --sql > migration.sql
```
- Replace <revision_or_head> with:
    A specific migration revision (e.g., 1234abcd).
    head for the latest migration.
## Store and Manage SQL Scripts
```
docker exec -i <db_container> psql -U <username> -d <database> < sql_migrations/002_add_new_table.sql

```

## docker image
property-street-backend