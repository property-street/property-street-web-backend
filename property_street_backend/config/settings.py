from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Secret key for cryptographic operations
SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')

# Debug mode
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# Allowed hosts for the application
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# SQLAlchemy database configuration for PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://user:password@localhost/dbname')

TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL', 'postgresql+asyncpg://user:password@localhost/dbname')

# CORS settings
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

# JWT settings
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your_jwt_secret_key')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA = int(os.getenv('JWT_EXPIRATION_DELTA', 30))

