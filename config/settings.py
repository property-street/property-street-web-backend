from pathlib import Path
from decouple import config


ENVIRONMENT = config("ENVIRONMENT")

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Secret key for cryptographic operations
SECRET_KEY = config('SECRET_KEY')

# Debug mode
DEBUG = True if ENVIRONMENT == 'development' else False

# Allowed hosts for the application
ALLOWED_HOSTS = config('ALLOWED_HOSTS').split(',')

# SQLAlchemy database configuration for PostgreSQL
DATABASE_URL = config('DATABASE_URL')

TEST_DATABASE_URL = config('TEST_DATABASE_URL')

# REDIS settings
REDIS_CACHE_DB = int(config('REDIS_CACHE_DB'))
TEST_REDIS_CACHE_DB = int(config('TEST_REDIS_CACHE_DB'))
NEWLY_CREATED_ASSET_TTL = int(config('NEWLY_CREATED_ASSET_TTL'))
SEARCH_UNIT_TTL = int(config('SEARCH_UNIT_TTL'))
REDIS_HOST = config('TEST_REDIS_HOST') if DEBUG else config('REDIS_HOST')
CART_OFFLOAD_SCHEDULE =  config('TEST_CART_OFFLOAD_SCHEDULE') if DEBUG else config('CART_OFFLOAD_SCHEDULE')

# CORS settings
CORS_ORIGINS = config('CORS_ORIGINS').split(',')

# JWT settings
JWT_SECRET_KEY = config('JWT_SECRET_KEY')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA = int(config('JWT_EXPIRATION_DELTA'))

# google credentials
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URL = config('TEST_GOOGLE_REDIRECT_URL') if DEBUG else config('PROD_GOOGLE_CLIENT_SECRET')