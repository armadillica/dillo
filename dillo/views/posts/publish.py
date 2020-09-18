import json
import logging
import subprocess

import magic
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import SuspiciousOperation
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import FormView

from dillo import forms
from dillo.models.posts import Post, PostWithMedia, PostMediaImage, PostMediaVideo, PostMedia

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
        post_with_media, _ = PostWithMedia.objects.get_or_create(user=request.user, status='draft')

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
    """"Uploads a file and returns PostMedia id.

    The PostMedia id is used in Dropzone to allow the deletion of the upload.
    """

    # TODO(fsiddi) Refactor as class-based view

    def check_in_memory_mime(in_memory_file):
        mime = magic.from_buffer(in_memory_file.read(), mime=True)
        return mime

    # Ensure that only post owner can upload files for this post
    post = get_object_or_404(Post, hash_id=hash_id)
    if request.user != post.user:
        return JsonResponse({'error': 'Not allowed to upload on this post.'}, status=422)

    # Ensure that request.FILES contains only one file. We allow only
    # one file upload per request in order to return the PostMedia id
    # that was created in the response.
    if len(request.FILES) > 1:
        return JsonResponse({'error': 'Only one file per request is allowed.'}, status=422)

    in_memory_file = next(iter(request.FILES.values()))

    mime_type = check_in_memory_mime(in_memory_file)
    if mime_type not in settings.MEDIA_UPLOADS_ACCEPTED_MIMES:
        log.info('MIME type %s not accepted for upload' % mime_type)
        return JsonResponse({'error': 'This file type is not accepted.'}, status=422)

    if mime_type.startswith('image'):
        image = PostMediaImage.objects.create(
            image=in_memory_file, source_filename=in_memory_file.name[:128]
        )
        log.debug('Attaching image to unpublished post %s' % post.hash_id)
        post_media = post.postmedia_set.create(content_object=image)
    elif mime_type.startswith('video'):
        video = PostMediaVideo.objects.create(
            source=in_memory_file, source_filename=in_memory_file.name[:128]
        )

        log.debug('Processing video %s', video.source.path)
        try:
            video_data = process_video_data(video.source.path)
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
        post_media = post.postmedia_set.create(content_object=video)
    else:
        log.error('Unknown upload type %s' % mime_type)
        return JsonResponse({'error': 'This file type is not accepted.'}, status=422)

    return JsonResponse({'status': 'success', 'post_media_id': post_media.id})


@require_POST
@login_required
def post_get_unpublished_uploads(request, hash_id):
    """Return list of uploaded files for a pending post."""
    post = get_object_or_404(Post, hash_id=hash_id)
    if request.user != post.user:
        return JsonResponse({'error': 'Not allowed work on this post.'}, status=422)

    post_media_list = []
    for post_media in post.postmedia_set.all():
        if isinstance(post_media.content_object, PostMediaImage):
            post_media.content_object.source = post_media.content_object.image
        post_media_list.append(
            {
                'name': str(post_media.content_object),
                'size': post_media.content_object.source.size,
                'url': post_media.content_object.source.url,
                'post_media_id': post_media.id,
            }
        )
    return JsonResponse({'media': post_media_list})


@require_POST
@login_required
def delete_unpublished_upload(request, hash_id):
    """Delete a media object, if the post is not published."""
    post = get_object_or_404(Post, hash_id=hash_id)

    # Ensure User owns the Post
    if request.user != post.user:
        return JsonResponse({'error': 'Not allowed to remove this item.'}, status=422)

    # Ensure Post is in 'draft' status
    if post.status != 'draft':
        return JsonResponse({'error': 'Post media can be removed only from drafts.'}, status=422)

    # Ensure post_media_id is provided
    if 'post_media_id' not in request.POST:
        log.error('filepath not provided in order to delete unpublished upload')
        return JsonResponse({'error': 'Filepath not provided.'}, status=400)

    # Ensure post_media_id is an integer
    try:
        post_media_id = int(request.POST['post_media_id'])
    except ValueError:
        log.error('Attempting to convert %s to int' % request.POST['post_media_id'])
        return JsonResponse({'error': 'PostMedia id is not valid.'}, status=400)

    # Try to fetch PostMedia based on id and current post
    try:
        post_media = PostMedia.objects.get(pk=post_media_id, post=post)
    except PostMedia.DoesNotExist:
        return JsonResponse({'error': 'Media not found.'}, status=400)

    log.info('Deleting unpublished PostMedia %i' % post_media_id)
    post_media.delete()
    return JsonResponse({'status': 'OK'})


@require_POST
@csrf_exempt
def post_update_video_processing(request, hash_id, video_id):
    """Endpoint used by Coconut to update us on video processing."""
    if request.content_type != 'application/json':
        raise SuspiciousOperation('Coconut webhook was sent non-JSON data')
    job = json.loads(request.body)
    post = get_object_or_404(Post, hash_id=hash_id)
    log.info('Updating video %i processing status to %s' % (video_id, job['event']))
    post.update_video_processing_status(video_id, job)

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
