import os
import socket
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load your custom env file first
load_dotenv(".env.backend")

DEV_ENV_HOSTNAME = os.getenv("DEV_ENV_HOSTNAME")

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Debug mode
DEBUG = socket.gethostname() == DEV_ENV_HOSTNAME

# Allowed hosts for the application
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS').split(',')

ENVIRONMENT = os.getenv('ENVIRONMENT')

# SQLAlchemy database configuration for PostgreSQL
DEV_DATABASE_URL = os.getenv('DEV_DATABASE_URL')
PROD_DATABASE_URL = os.getenv('PROD_DATABASE_URL')
TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL')

EMAIL_VERIFICATION_CODE_TTL = 300
TEST_EMAIL_VERIFICATION_CODE_TTL = 60

PASSWORD_LINK_TTL = 3600 # 1 hr
TEST_PASSWORD_LINK_TTL = 60

# REDIS cache db
PROD_REDIS_CACHE_DB=0
TEST_REDIS_CACHE_DB=1
REDIS_CACHE_DB = TEST_REDIS_CACHE_DB if DEBUG else PROD_REDIS_CACHE_DB

# REDIS host
PROD_REDIS_HOST = "redis"
TEST_REDIS_HOST = "localhost"
REDIS_HOST = TEST_REDIS_HOST if DEBUG else PROD_REDIS_HOST
DEV_REDIS_URL=os.getenv('DEV_REDIS_URL')
PROD_REDIS_URL=os.getenv('PROD_REDIS_URL')
REDIS_URL = DEV_REDIS_URL if DEBUG else PROD_REDIS_URL

# newly created asset ttl
TEST_NEWLY_CREATED_ASSET_TTL = 3 # seconds
NEWLY_CREATED_ASSET_TTL = 7776000 # 90 days

# password update ttl
TEST_PASSWORD_UPDATE_TTL = 3 # 3 seconds
PASSWORD_UPDATE_TTL = 3600 # 1 hr

# search unit ttl
SEARCH_UNIT_TTL = 2592000 # 30 days

# auto offload; 1 day
PROD_CART_OFFLOAD_SCHEDULE =  86400 # 1 day
TEST_CART_OFFLOAD_SCHEDULE =  12
CART_OFFLOAD_SCHEDULE = TEST_CART_OFFLOAD_SCHEDULE if DEBUG else PROD_CART_OFFLOAD_SCHEDULE

# chat lazy offload schedule
CHAT_LAZY_OFFLOAD_SCHEDULE = 10800 # 3 hours
TEST_CHAT_LAZY_OFFLOAD_SCHEDULE = 3

# ttl for items in a cart (seconds)
TEST_CART_TTL = 2
PROD_CART_TTL = 2592000 # 30 days

# chat TTL
CHAT_TTL = 86400 # 24 hours
TEST_CHAT_TTL = 60

# agent notification entry deletion schedule
TEST_AGENT_NOTIFICATION_ENTRY_OFFLOAD_SCHEDULE = 7
AGENT_NOTIFICATION_ENTRY_OFFLOAD_SCHEDULE = 604800 # 7 days

# CORS settings
CORS_ORIGINS = os.getenv('CORS_ORIGINS').split(',')

# JWT settings
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA=1440
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

# google credentials
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
TEST_GOOGLE_REDIRECT_URL = "http://localhost:8080/google_oauth/callback"
PROD_GOOGLE_REDIRECT_URL = "https://propertystreet.ng:8080/google_oauth/callback"
GOOGLE_REDIRECT_URL = TEST_GOOGLE_REDIRECT_URL if DEBUG else PROD_GOOGLE_REDIRECT_URL

ADMIN_EMAIL=os.getenv("ADMIN_EMAIL")
ADMIN_USERNAME=os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD")
REAL_TEST_EMAIL=os.getenv("REAL_TEST_EMAIL")

# staff link validity
STAFF_LINK_VALIDITY=86400  # in seconds (1 day) 
TEST_STAFF_LINK_VALIDITY=2  # in seconds (2 seconds))

# staff link validity
BETA_LINK_VALIDITY=86400  # in seconds (1 day) 
TEST_BETA_LINK_VALIDITY=2  # in seconds (2 seconds))

# Beta launching
BETA_LAUNCHING = True 
BETA_LAUNCH_PROPERTY_LIMIT = 5

CLOUDINARY_API_KEY=os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET=os.getenv("CLOUDINARY_API_SECRET")

TEST_ROUTINE_STALE_CLOUD_PUBID_DELETION=10 # 1 SECS
ROUTINE_STALE_CLOUD_PUBID_DELETION=86400 # 1 day

# Cloudinary redis lock expiry
CLOUDINARY_DELETION_LOCK_EXPIRY =  86400 # 1 day
TEST_CLOUDINARY_DELETION_LOCK_EXPIRY =  12 # 12 seconds