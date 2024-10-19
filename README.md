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
    ipython -i Scripts/ipython_config.py
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