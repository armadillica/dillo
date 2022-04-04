import os

from tests.settings_common import *

AWS_ACCESS_KEY_ID = 'CHANGE_ME'
AWS_SECRET_ACCESS_KEY = 'CHANGE_ME'
AWS_CLOUDFRONT_KEY_ID = os.environ.get('AWS_CLOUDFRONT_KEY_ID')
AWS_CLOUDFRONT_KEY = os.environ.get('AWS_CLOUDFRONT_KEY', '').encode('ascii')

RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''
