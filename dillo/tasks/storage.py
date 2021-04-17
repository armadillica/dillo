import logging
import tempfile
from urllib.parse import urlparse

import boto3
import requests
from django.conf import settings
from django.core.files.images import ImageFile

import dillo.models

log = logging.getLogger(__name__)

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def get_storage_paths() -> (str, str):
    """Get storage paths depending on DEFAULT_FILE_STORAGE."""
    storage_backend = settings.DEFAULT_FILE_STORAGE

    if storage_backend == 'django.core.files.storage.FileSystemStorage':
        # The base SFTP path, with credentials
        storage_base_src = settings.COCONUT_SFTP_STORAGE
        storage_base_dst = storage_base_src

        # Override settings if debug mode
        if settings.DEBUG:
            storage_base_src = f'{settings.COCONUT_DECLARED_HOSTNAME}/media/'
            storage_base_dst = f'{settings.COCONUT_DECLARED_HOSTNAME}/debug-video-transfer/'

        return storage_base_src, storage_base_dst
    elif storage_backend == 'storages.backends.s3boto3.S3Boto3Storage':
        return (
            f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/",
            f"s3://{settings.AWS_ACCESS_KEY_ID}:{settings.AWS_SECRET_ACCESS_KEY}@"
            f"{settings.AWS_UPLOADS_BUCKET_NAME}/",
        )
    else:
        raise ValueError('Unsupported storage_backend: %s' % storage_backend)


def download_image_from_web(url, attribute):
    # Build request (streaming)
    r = requests.get(url, stream=True)
    # Get the path component from the url
    path_comp = urlparse(url)[2]
    hashed_path = dillo.models.mixins.get_upload_to_hashed_path(None, path_comp)

    # Download the file
    with tempfile.TemporaryFile() as fp:
        log.debug("Downloading file %s to %s" % (url, fp.name))
        for chunk in r.iter_content(chunk_size=128):
            fp.write(chunk)
        log.debug("Assigning file to model instance")
        attribute.save(str(hashed_path), ImageFile(fp))
