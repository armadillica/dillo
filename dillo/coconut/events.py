# Collection of functions used when the coconut_webhook is called

import logging
from urllib.parse import urlparse

from django.conf import settings
from django.http.response import JsonResponse
from dillo.models.posts import Post
from dillo.models.static_assets import Video
from dillo.tasks import move_blob_from_upload_to_storage

log = logging.getLogger(__name__)


def source_transferred(job: dict, video: Video):
    """Handle a source.transferred event."""
    # Get the first (and usually only) video stream
    source_streams = job['metadata']['source']['streams']
    video_stream = next(item for item in source_streams if item['codec_type'] == 'video')

    # Set Video properties
    video.aspect = video_stream['width'] / video_stream['height']
    video.framerate = int(video_stream['r_frame_rate'].split('/')[0])
    video.save()


def output_processed_images(job: dict, video: Video):
    """Handle an output.processed event for image files."""
    # Images urls are provided in a list, because the 'image' format allows
    # for the possibility of specifying more than one image.
    # The current implementation of video processing expects there to be only
    # one image, used as thumbnail. For this reason we get the first element
    # of the 'urls' list.
    if video.static_asset.thumbnail:
        log.debug('Video %i already has a thumbnail, not updating' % video.id)
        return JsonResponse({'status': 'ok'})
    source_path = urlparse(job['urls'][0]).path.strip('/')

    if settings.DEFAULT_FILE_STORAGE == 'storages.backends.s3boto3.S3Boto3Storage':
        move_blob_from_upload_to_storage(source_path)

    video.static_asset.thumbnail = source_path
    video.static_asset.save()


def output_processed_video(job: dict, video: Video):
    """Handle an output.processed event for a video file."""
    source_path = urlparse(job['url']).path.strip('/')
    # Move the encoded video to the final location
    if settings.DEFAULT_FILE_STORAGE == 'storages.backends.s3boto3.S3Boto3Storage':
        move_blob_from_upload_to_storage(source_path)


def job_completed(job: dict, video: Video, post: Post):
    video.encoding_job_status = job['event']  # job.completed
    video.save()
    if not post.may_i_publish:
        return
    log.debug('Video has been processed, attempting to publish')
    post.publish()
