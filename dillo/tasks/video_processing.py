import pathlib
import logging

from background_task import background
from django.conf import settings
from django.urls import reverse

import dillo.coconut.job
import dillo.models.static_assets
from dillo.tasks.storage import get_storage_paths

log = logging.getLogger(__name__)


@background()
def create_coconut_job(post_hash_id: str, video_id: int):
    """Create a video encoding job.

    Because of the @background decorator, we only accept hashable
    arguments.

    The video versions produced are the following:
    - a regular 720p, h264 with mp4 container
    - an httpstream using fragmented mp4, compatible with DASH and HLS
      with two variants (these are WIP and should be tweaked):
      - mp4:480p_1500k
      - mp4:720p
    """
    if not settings.COCONUT_API_KEY:
        log.info('Missing COCONUT_API_KEY: no video encoding will be performed')
        return

    storage_base_src, storage_base_dst = get_storage_paths()

    # Outputs
    outputs = {}

    video = dillo.models.static_assets.Video.objects.get(id=video_id)
    source_path = pathlib.PurePath(video.static_asset.source.name)

    # The jpg:1280x thumbnail
    outputs['jpg:1280x'] = f"{storage_base_dst}{source_path.with_suffix('.thumbnail.jpg')}"

    # The gif:240x preview
    outputs['gif:240x'] = f"{storage_base_dst}{source_path.with_suffix('.preview.gif')}"

    # The mp4:720p version of the path (relative to MEDIA_ROOT)
    outputs['mp4:0x720_3000k'] = f"{storage_base_dst}{source_path.with_suffix('.720p.mp4')}"

    # The httpstream packaging configuration
    httpstream_packaging = 'dash+hlsfmp4=/stream'

    # The httpstream variants
    httpstream_variants = 'variants=mp4:480p_1500k,mp4:720p'

    # TODO(fsiddi) enable support for httpstream
    # outputs['httpstream'] = f'{job_storage_base_out}{source_path.parent}, ' \
    #     f'{httpstream_packaging}, {httpstream_variants}'

    # Webhook for encoding updates
    job_webhook = reverse('coconut-webhook', kwargs={'hash_id': post_hash_id, 'video_id': video_id})

    j = dillo.coconut.job.create(
        api_key=settings.COCONUT_API_KEY,
        source=f'{storage_base_src}{source_path}',
        webhook=f'{settings.COCONUT_DECLARED_HOSTNAME}{job_webhook}, events=true, metadata=true',
        outputs=outputs,
    )

    if j['status'] == 'processing':
        log.info('Started processing job %i' % j['id'])
    else:
        log.error('Error processing job %i' % (j['id']))


if settings.BACKGROUND_TASKS_AS_FOREGROUND:
    # Will execute activity_fanout_to_feeds immediately
    log.debug('Executing background tasks synchronously')
    create_coconut_job = create_coconut_job.task_function
