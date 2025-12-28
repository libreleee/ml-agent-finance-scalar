import os
from datetime import timedelta

# Database
SQLALCHEMY_DATABASE_URI = 'postgresql://superset:superset@superset-db:5432/superset'

# Cache
CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_REDIS_HOST': 'superset-redis',
    'CACHE_REDIS_PORT': 6379,
}

# Security
SECRET_KEY = os.getenv('SUPERSET_SECRET_KEY', 'change-me-in-production')
SUPERSET_WEBSERVER_TIMEOUT = 60
ROW_LIMIT = 10000

# Features
SUPERSET_FEATURE_FLAGS = {
    'ALLOW_USER_PROFILE_EDIT': True,
    'ENABLE_FORMULA_EDITING': True,
}
