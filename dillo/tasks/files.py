import logging

from background_task import background
from django.conf import settings

from dillo.tasks.storage import s3_client

log = logging.getLogger(__name__)


def move_blob_from_upload_to_storage(key):
    """Move a blob from the upload bucket to the permanent location."""
    try:
        log.info(
            'Copying %s/%s to %s'
            % (settings.AWS_UPLOADS_BUCKET_NAME, key, settings.AWS_STORAGE_BUCKET_NAME)
        )
        s3_client.copy_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key,
            CopySource={'Bucket': settings.AWS_UPLOADS_BUCKET_NAME, 'Key': key},
            MetadataDirective="REPLACE",
        )
    except Exception as e:
        log.error('Generic exception on %s' % key)
        log.error(str(e))
        return

    log.debug('Deleting %s from upload bucket' % key)
    s3_client.delete_object(
        Bucket=settings.AWS_UPLOADS_BUCKET_NAME, Key=key,
    )


@background()
def async_move_blob_from_upload_to_storage(key):
    """Call the actual move function.

    This is done because in AttachS3MediaToEntity we have to call
    move_blob_from_upload_to_storage synchronously. Since we have a
    BACKGROUND_TASKS_AS_FOREGROUND setting, this would be a problem.
    """
    move_blob_from_upload_to_storage(key)


if settings.BACKGROUND_TASKS_AS_FOREGROUND:
    # Will execute activity_fanout_to_feeds immediately
    log.debug('Executing background tasks synchronously')
    async_move_blob_from_upload_to_storage = async_move_blob_from_upload_to_storage.task_function
