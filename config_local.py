import os

DEBUG = True
SCHEME = 'http'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'
os.environ['PILLAR_MONGO_DBNAME'] = 'dillo'
os.environ['PILLAR_MONGO_HOST'] = '192.168.99.100'


STORAGE_DIR = '/Users/fsiddi/Documents/docker/dillo/storage'
SHARED_DIR = STORAGE_DIR

PILLAR_SERVER_ENDPOINT = 'http://dillo:5000/api/'

SOCIAL_BLENDER_ID = {
    'app_id': 'DILLO',
    'app_secret': 'thohghoh5XeisodoThaateewo2chooy3'
}
BLENDER_ID_BASE_URL = 'http://blender_id:8000/'
# BLENDER_ID_BASE_URL = 'https://www.blender.org/id/'
BLENDER_ID_OAUTH_URL = BLENDER_ID_BASE_URL + 'api/'
BLENDER_ID_BASE_ACCESS_TOKEN_URL = BLENDER_ID_BASE_URL + 'oauth/token'
BLENDER_ID_AUTHORIZE_URL = BLENDER_ID_BASE_URL + 'oauth/authorize'

GCLOUD_APP_CREDENTIALS = '/Users/fsiddi/Documents/docker/dillo/config/google_app.json'
GCLOUD_PROJECT = os.environ.get(
    'GCLOUD_PROJECT', 'blender-cloud-dev'
)

MAIN_PROJECT_ID = '58712f8cea893b11b51402bf'
URLER_SERVICE_AUTH_TOKEN = 'SRV9nQ3r7e9VoVDHUENLb9M5w0Toxsxgjjy6ErpfuBUvO0'

ALGOLIA_USER = '94FQ6RMSIC'
ALGOLIA_PUBLIC_KEY = '040eb31a45d5b48b5030dd192efc2002'
ALGOLIA_INDEX_USERS = 'dev_Users'
ALGOLIA_INDEX_NODES = 'dev_Nodes'

LOGGING = {
    'version': 1,
    'formatters': {
        'default': {'format': '%(asctime)-15s %(levelname)8s %(name)s %(message)s'}
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stderr',
        }
    },
    'loggers': {
        'pillar': {'level': 'DEBUG'},
        'werkzeug': {'level': 'DEBUG'},
    },
    'root': {
        'level': 'WARNING',
        'handlers': [
            'console',
        ],
    }
}