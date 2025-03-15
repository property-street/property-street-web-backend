# Property Street Backend


## Starting the development server
```bash
fastapi run --port 8080
```

## Starting the redis server
```bash
sudo service redis-server start
```

## Running tests
```bash
pytest path_to_test_script
```


## activate the fast api shell
```bash
  ipython -i scripts/ipython_config.py
``` 


## Configure alembic.ini and env.py for your database

### initialize alembic
```bash
alembic init alembic
```

### Generate a new migration
```bash
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
```bash
alembic upgrade <revision_or_head> --sql > <path/to/migration.sql>
```
- Replace <revision_or_head> with:
    A specific migration revision (e.g., 1234abcd).
    head for the latest migration.
### temporarily copy to the container's tmp directory
```bash
docker cp /local_path/to/migration_script.sql <container_name>:/tmp/migration_script.sql
```
### Migate the database using the copied SQL Scripts
```bash
docker exec -it <db_container> \
  bash -c 'PGPASSWORD=<password> psql -h <hostname> -U <username> -d <database> -f /tmp/migration_script.sql'
```

## build image to docker hub repo
docker build -t crankgig/property_street_docker_hub_fastapi_repo:latest .
### push the image to docker hub
docker push crankgig/property_street_docker_hub_fastapi_repo:latest