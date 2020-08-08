import pathlib

BASE_DIR = pathlib.Path(__file__).absolute().parent.parent

DEBUG = True
USE_TZ = True
TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-us'

SECRET_KEY = 'test'
SITE_ID = 1  # Required by django-allauth

ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_TEMPLATE_EXTENSION = 'pug'

ACCOUNT_FORMS = {
    'signup': 'dillo.forms.CustomSignupForm',
}

ROOT_URLCONF = 'tests.urls'

INSTALLED_APPS = [
    'dillo.apps.DilloConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Required by django-allauth
    'django.contrib.flatpages',
    'django.contrib.postgres',
    'pipeline',
    'background_task',
    'taggit',
    'actstream',
    'anymail',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'sorl.thumbnail',
    'tinymce',
    'crispy_forms',
    'loginas',
    'djversion',
    'micawber.contrib.mcdjango',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'public/static'
MEDIA_ROOT = BASE_DIR / 'public/media'

BACKGROUND_TASKS_AS_FOREGROUND = True
HASHID_FIELD_SALT = 'salt'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # 'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dillo.context_processors.notifications_count',
                'dillo.context_processors.google_analytics_tracking_id',
                'dillo.context_processors.default_og_data',
                'dillo.context_processors.media_uploads_accepted_mimes',
            ],
            # PyPugJS:
            'loaders': [
                (
                    'pypugjs.ext.django.Loader',
                    (
                        'django.template.loaders.filesystem.Loader',
                        'django.template.loaders.app_directories.Loader',
                    ),
                )
            ],
            'builtins': ['pypugjs.ext.django.templatetags',],
        },
    },
]

PIPELINE = {
    # 'PIPELINE_ENABLED': True,
    'JS_COMPRESSOR': 'pipeline.compressors.jsmin.JSMinCompressor',
    # Consider https://github.com/mysociety/django-pipeline-csscompressor
    'CSS_COMPRESSOR': 'pipeline.compressors.NoopCompressor',
    'JAVASCRIPT': {
        'vendor': {
            'source_filenames': (
                'js/vendor/jquery-*.js',
                'js/vendor/popper-*.js',
                'js/vendor/bootstrap-*.js',
                'js/vendor/videojs-*.js',
                'js/vendor/js.cookie-*.js',
                'js/vendor/mousetrap-*.js',
                'js/vendor/slick-*.js',
                'js/vendor/twemoji-*.js',
            ),
            'output_filename': 'js/vendors.js',
        },
        'vendor_dropzone': {
            'source_filenames': ('js/vendor/dropzone-*.js',),
            'output_filename': 'js/dropzone.js',
        },
        'vendor_jquery_formset': {
            'source_filenames': ('js/vendor/jquery-formset-*.js',),
            'output_filename': 'js/jquery_formset.js',
        },
        'tutti': {'source_filenames': ('js/tutti/*.js',), 'output_filename': 'js/tutti.js',},
        'tutti_user': {
            'source_filenames': (
                'js/tutti_user/avatar_preview*.js',
                'js/tutti_user/utils*.js',
                'js/tutti_user/ui*.js',
                'js/tutti_user/posts*.js',
                'js/tutti_user/comments*.js',
            ),
            'output_filename': 'js/tutti_user.js',
        },
    },
    'STYLESHEETS': {
        'main': {
            'source_filenames': ('styles/main.sass',),
            'output_filename': 'css/main.css',
            'extra_context': {'media': 'screen,projection',},
        },
        'edit': {
            'source_filenames': ('styles/edit.sass',),
            'output_filename': 'css/edit.css',
            'extra_context': {'media': 'screen,projection',},
        },
    },
    'COMPILERS': ('libsasscompiler.LibSassCompiler',),
    'DISABLE_WRAPPER': True,
}

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'
# STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'dillo',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

GOOGLE_ANALYTICS_TRACKING_ID = ''

MEDIA_UPLOADS_ACCEPTED_MIMES = {
    'image/png',
    'image/jpeg',
    'video/mp4',
    'video/quicktime',
    'video/x-matroska',
    'video/avi',
    'video/mpeg',
}

MEDIA_UPLOADS_VIDEO_MAX_DURATION_SECONDS = 60 * 4

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {'format': '%(levelname)8s %(name)s %(message)s'},
        'verbose': {
            'format': '%(asctime)-15s %(levelname)8s %(name)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'default',},},
    'loggers': {'dillo': {'handlers': ['console'], 'level': 'DEBUG'},},
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = "Animato <contact@anima.to>"
