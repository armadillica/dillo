import json
import logging
import pathlib
import subprocess

import magic
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import SuspiciousOperation
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import FormView

from dillo import forms
from dillo.models.posts import Post
from dillo.models.static_assets import StaticAsset, Video, Image
from dillo.models.mixins import get_upload_to_hashed_path
from dillo.tasks.files import move_blob_from_upload_to_storage
from dillo.coconut import events
from dillo.templatetags.dillo_filters import compact_number

log = logging.getLogger(__name__)


class PostCreateView(LoginRequiredMixin, FormView):
    """Form view for the creation of a new post."""

    template_name = 'dillo/post_create.pug'
    form_class = forms.PostForm
    success_url = '/'

    image = None
    post_instance = None

    def get(self, request, *args, **kwargs):
        # Get an existing post in draft status
        # Note: this makes it impossible for a user to create multiple
        # posts in parallel.
        post_with_media, _ = Post.objects.get_or_create(user=request.user, status='draft')

        self.initial = {'post_id': post_with_media.id}
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        context = self.get_context_data(**kwargs)
        context['form'] = form
        context['post'] = post_with_media
        return self.render_to_response(context)

    def form_valid(self, form):
        self.post_instance.title = form.cleaned_data['title']
        self.post_instance.save()
        self.post_instance.process_videos()
        if self.post_instance.may_i_publish:
            self.post_instance.publish()
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            p = Post.objects.get(pk=form.cleaned_data['post_id'])
            if p.user != request.user:
                raise SuspiciousOperation(
                    'User %i tried to edit a Post from User %i' % (request.user.id, p.user.id)
                )
            self.post_instance = p
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


def get_video_data_with_ffprobe(filepath) -> dict:
    """Return video duration and resolution given an input file path."""
    ffprobe_inspect = [
        'ffprobe',
        '-loglevel',
        'error',
        '-show_streams',
        filepath,
        '-print_format',
        'json',
    ]

    return json.loads(subprocess.check_output(ffprobe_inspect))


def process_video_data(filepath):
    ffprobe_output = get_video_data_with_ffprobe(filepath)
    video_stream = None

    # Loop through audio and video streams searching for the video
    for stream in ffprobe_output['streams']:
        if stream['codec_type'] == 'video':
            video_stream = stream

    # Stop if no video_stream is found
    if not video_stream:
        raise RuntimeError('No video stream found in filepath')

    # If we can't determine the video duration, something went wrong
    if 'duration' not in video_stream:
        raise RuntimeError('Video file does not have a duration')

    duration = int(float(video_stream['duration']))

    # Get framerate value by processing the ffprobe value, for example
    # "avg_frame_rate": "24/1"
    avg_framerate = video_stream['avg_frame_rate']
    avg_framerate_split = avg_framerate.split('/')

    framerate = int(int(avg_framerate_split[0]) / int(avg_framerate_split[1]))
    aspect = video_stream['width'] / video_stream['height']

    outdata = dict(
        duration=duration,
        res_x=video_stream['width'],
        res_y=video_stream['height'],
        framerate=framerate,
        aspect=aspect,
    )

    if 'sample_aspect_ratio' not in video_stream:
        log.warning("Missing aspect ratio info for %s" % filepath)

    if 'sample_aspect_ratio' in video_stream and video_stream['sample_aspect_ratio'] != '1:1':
        log.error('Pixel aspect ratio is not square!')

    return outdata


@require_POST
@login_required
def post_file_upload(request, hash_id):
    """"Uploads a file and returns Attachment id.

    The Attachment id is used in the upload area to allow the deletion of the upload.
    """

    # TODO(fsiddi) Refactor as class-based view

    def check_in_memory_mime(in_memory_file):
        mime = magic.from_buffer(in_memory_file.read(), mime=True)
        return mime

    Post.objects.get(hash_id=hash_id)
    # Ensure that only post owner can upload files for this post
    post = get_object_or_404(Post, hash_id=hash_id)
    if not post.can_edit(request.user):
        return JsonResponse({'error': 'Not allowed to upload on this post.'}, status=422)
    # Ensure that request.FILES contains only one file. We allow only
    # one file upload per request in order to return the Media id
    # that was created in the response.
    if len(request.FILES) > 1:
        return JsonResponse({'error': 'Only one file per request is allowed.'}, status=422)

    in_memory_file = next(iter(request.FILES.values()))

    mime_type = check_in_memory_mime(in_memory_file)
    if mime_type not in settings.MEDIA_UPLOADS_ACCEPTED_MIMES:
        log.info('MIME type %s not accepted for upload' % mime_type)
        return JsonResponse({'error': 'This file type is not accepted.'}, status=422)

    static_asset = StaticAsset.objects.create(
        source=in_memory_file, source_filename=in_memory_file.name[:128],
    )

    if mime_type.startswith('image'):
        static_asset.source_type = 'image'
        static_asset.save()
        Image.objects.create(static_asset=static_asset)
        log.debug('Attaching image to unpublished post %s' % post.hash_id)
        post.media.add(static_asset)
    elif mime_type.startswith('video'):
        static_asset.source_type = 'video'
        static_asset.save()
        video = Video.objects.create(static_asset=static_asset)

        log.debug('Processing video %s', video.static_asset.source.path)
        try:
            video_data = process_video_data(video.static_asset.source.path)
        except RuntimeError as e:
            log.debug(e)
            return JsonResponse({'error': 'We could not process the video file.'}, status=500)

        if video_data['duration'] > settings.MEDIA_UPLOADS_VIDEO_MAX_DURATION_SECONDS:
            log.warning('Video has duration of %i sec. and was rejected' % video_data['duration'])
            # Delete the video entry
            video.delete()
            return JsonResponse(
                {
                    'error': 'This video is longer than %i seconds. '
                    'Please upload a video that lasts less than that'
                    % settings.MEDIA_UPLOADS_VIDEO_MAX_DURATION_SECONDS
                },
                status=422,
            )

        log.debug('Update video entry with info about framerate and aspect ratio')
        video.framerate = video_data['framerate']
        video.aspect = video_data['aspect']
        video.save()
        log.debug('Attaching video to unpublished post %s' % post.hash_id)
        post.media.add(static_asset)
    else:
        log.error('Unknown upload type %s' % mime_type)
        return JsonResponse({'error': 'This file type is not accepted.'}, status=422)

    return JsonResponse({'status': 'success', 'entity_media_id': static_asset.id})


@require_POST
@login_required
def api_get_unpublished_uploads(request, content_type_id, hash_id):
    """Return list of uploaded files for a pending post."""
    content_type = ContentType.objects.get_for_id(content_type_id)
    entity = get_object_or_404(content_type.model_class(), hash_id=hash_id)
    if not entity.can_edit(request.user):
        return JsonResponse({'error': 'Not allowed work on this post.'}, status=422)

    media_list = []
    for entity_media in entity.media.all():
        media_list.append(
            {
                'name': entity_media.source_filename,
                'size': entity_media.source.size,
                'size_label': compact_number(entity_media.source.size),
                'url': entity_media.source.url,
                'entity_media_id': entity_media.id,
                'hash_id': entity_media.hash_id,
            }
        )
    return JsonResponse({'media': media_list})


@require_POST
@login_required
def api_delete_unpublished_upload(request, content_type_id, hash_id):
    """Delete a media object, if the post is not published."""
    content_type = ContentType.objects.get_for_id(content_type_id)
    entity = get_object_or_404(content_type.model_class(), hash_id=hash_id)

    # Ensure User can edit the Entity
    if not entity.can_edit(request.user):
        return JsonResponse({'error': 'Not allowed to remove this item.'}, status=422)

    # Ensure Post is in 'draft' status
    if entity.status != 'draft':
        return JsonResponse({'error': 'Post media can be removed only from drafts.'}, status=422)

    # Ensure entity_media_id is provided
    if 'entity_media_id' not in request.POST:
        log.error('filepath not provided in order to delete unpublished upload')
        return JsonResponse({'error': 'Filepath not provided.'}, status=400)

    # Ensure entity_media_id is an integer
    try:
        entity_media_id = int(request.POST['entity_media_id'])
    except ValueError:
        log.error('Attempting to convert %s to int' % request.POST['entity_media_id'])
        return JsonResponse({'error': 'Media id is not valid.'}, status=400)

    # Try to fetch Media based on id and current post
    try:
        post_media = entity.media.get(id=entity_media_id)
    except StaticAsset.DoesNotExist:
        return JsonResponse({'error': 'Media not found.'}, status=400)

    log.info('Deleting unpublished Media %i' % entity_media_id)
    post_media.delete()
    return JsonResponse({'status': 'OK'})


@require_POST
@csrf_exempt
def coconut_webhook(request, hash_id, video_id):
    """Endpoint used by Coconut to update us on video processing."""
    if request.content_type != 'application/json':
        raise SuspiciousOperation('Coconut webhook endpoint was sent non-JSON data')
    job = json.loads(request.body)
    post = get_object_or_404(Post, hash_id=hash_id)
    video = get_object_or_404(Video, id=video_id)
    if video.encoding_job_id != job['id']:
        # If the job id changed, we likely restarted the job (manually)
        video.encoding_job_status = None
        video.encoding_job_id = job['id']
        video.save()

    log.info('Updating video %i processing status: %s' % (video_id, job['event']))
    # On source.transferred
    if job['event'] == 'source.transferred':
        events.source_transferred(job, video)
    # On output.processed (thumbnail)
    elif job['event'] == 'output.processed' and job['format'].startswith('jpg'):
        events.output_processed_images(job, video)
    # On output.processed (video variation)
    elif job['event'] == 'output.processed' and (
        job['format'].startswith('mp4') or job['format'].startswith('gif')
    ):
        events.output_processed_video(job, video)
    # On job.completed (unused for now)
    elif job['event'] == 'job.completed':
        events.job_completed(job, video, post)
    return JsonResponse({'status': 'ok'})


@csrf_exempt
def debug_video_transfer(request, video_path):
    """Debug view to test video encoding during development."""
    # Skip entirely when not DEBUG
    if not settings.DEBUG:
        raise SuspiciousOperation('Attempting unallowed video upload')
    # Skip entirely unless POST request
    if request.method != 'POST':
        return JsonResponse({'status': 'ok'})

    # Get the video File
    video_file = request.FILES['encoded_video']
    # Build destination path
    dest_path = settings.MEDIA_ROOT / video_path
    with open(dest_path, 'wb+') as destination:
        for chunk in video_file.chunks():
            destination.write(chunk)
        log.info('Saved in %s' % dest_path)
    return JsonResponse({'status': 'ok'})


@login_required
def post_status(request, hash_id):
    """Returns post status, only for post owners."""
    post = get_object_or_404(Post, hash_id=hash_id)
    if post.user != request.user:
        raise SuspiciousOperation(
            "User %i tried to check post %i status" % (request.user.id, post.id)
        )
    return JsonResponse({'status': post.status})


@require_POST
@csrf_exempt
@login_required
def get_aws_s3_signed_url(request) -> JsonResponse:
    """Generate a pre-signed S3 POST URL."""

    body = json.loads(request.body)

    s3_client = boto3.client(
        's3',
        'eu-central-1',  # Not specifying this breaks.
        config=BotoConfig(s3={'addressing_style': 'path'}),
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    path = get_upload_to_hashed_path(None, body['filename'])
    try:
        response = s3_client.generate_presigned_post(
            settings.AWS_UPLOADS_BUCKET_NAME,
            str(path),
            Fields=None,
            Conditions=None,
            ExpiresIn=600,
        )
    except ClientError as e:
        logging.error(e)
        raise SuspiciousOperation("Error while creating signed url")

    return JsonResponse({'method': 'POST', 'url': response['url'], 'fields': response['fields']})


class AttachS3MediaToEntity(LoginRequiredMixin, FormView):
    http_method_names = ['post']
    form_class = forms.AttachS3MediaToEntityForm

    def process_file_type(self, entity, mime_type, key, name, size_bytes):
        if mime_type not in settings.MEDIA_UPLOADS_ACCEPTED_MIMES:
            log.info('MIME type %s not accepted for upload' % mime_type)
            return JsonResponse({'error': 'This file type is not accepted.'}, status=422)

        # Move file from upload to storage bucket, synchronously
        move_blob_from_upload_to_storage(key)

        if mime_type.startswith('image'):
            source_type = 'image' if 'gif' not in mime_type else 'video'
        elif mime_type.startswith('video'):
            source_type = 'video'
        else:
            log.error('Unknown upload type %s' % mime_type)
            return JsonResponse({'error': 'This file type is not accepted.'}, status=422)

        static_asset = StaticAsset.objects.create(
            source=key, source_filename=name, source_type=source_type,
        )
        static_asset.refresh_from_db()
        log.debug('Attaching %s to unpublished entity %s' % (source_type, entity.hash_id))
        entity.media.add(static_asset)

        return JsonResponse(
            {'status': 'ok', 'entity_media_id': static_asset.id, 'hashId': static_asset.hash_id}
        )

    def form_valid(self, form):
        content_type = ContentType.objects.get_for_id(form.cleaned_data['content_type_id'])
        entity = get_object_or_404(content_type.model_class(), id=form.cleaned_data['entity_id'])
        if not entity.can_edit(self.request.user):
            return JsonResponse({'error': 'Not allowed to upload on this post.'}, status=422)
        return self.process_file_type(
            entity,
            form.cleaned_data['mime_type'],
            form.cleaned_data['key'],
            form.cleaned_data['name'],
            form.cleaned_data['size_bytes'],
        )

    def form_invalid(self, form):
        # TODO(fsiddi) Improve error messages
        return JsonResponse({'status': 'error', 'message': 'Invalid form.'}, status=400)


class AddS3DownloadableToEntity(LoginRequiredMixin, FormView):
    http_method_names = ['post']
    form_class = forms.AttachS3MediaToEntityForm

    def process_file_type(self, entity, mime_type, key, name, size_bytes):
        # Move file from upload to storage bucket, synchronously
        move_blob_from_upload_to_storage(key)

        if mime_type.startswith('image'):
            static_asset = StaticAsset.objects.create(
                source=key, source_filename=name, source_type='image', size_bytes=size_bytes
            )
            log.debug('Attaching image to unpublished entity %s' % entity.hash_id)

        elif mime_type.startswith('video'):
            static_asset = StaticAsset.objects.create(
                source=key, source_filename=name, source_type='video', size_bytes=size_bytes
            )
            log.debug('Attaching video to unpublished entity %s' % entity.hash_id)
        else:
            static_asset = StaticAsset.objects.create(
                source=key, source_filename=name, size_bytes=size_bytes
            )
            log.debug('Attaching file to unpublished entity %s' % entity.hash_id)

        # Remove existing downloadable item, if it exists
        if entity.downloadable:
            entity.downloadable.delete()

        entity.downloadable = static_asset
        entity.save()

        return JsonResponse({'status': 'ok', 'static_asset_id': static_asset.id})

    def form_valid(self, form):
        content_type = ContentType.objects.get_for_id(form.cleaned_data['content_type_id'])
        entity = get_object_or_404(content_type.model_class(), id=form.cleaned_data['entity_id'])
        if not entity.can_edit(self.request.user):
            return JsonResponse({'error': 'Not allowed to upload on this entity.'}, status=422)
        return self.process_file_type(
            entity,
            form.cleaned_data['mime_type'],
            form.cleaned_data['key'],
            form.cleaned_data['name'],
            form.cleaned_data['size_bytes'],
        )

    def form_invalid(self, form):
        # TODO(fsiddi) Improve error messages
        return JsonResponse({'status': 'error', 'message': 'Invalid form.'}, status=400)
