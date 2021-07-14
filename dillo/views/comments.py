import sorl.thumbnail
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from dillo import forms
from dillo.models.comments import Comment
from dillo.templatetags.dillo_filters import markdown_with_parsed_tags_and_shortcodes
from dillo.templatetags.dillo_filters import compact_naturaltime
from dillo.templatetags.dillo_filters import is_moderator
from dillo.markdown import sanitize


class CommentsListView(ListView):
    """List of all published comments."""

    context_object_name = 'comments'
    template_name = 'dillo/comments_list.pug'

    def get_queryset(self):
        return (
            Comment.objects.filter(
                post__hash_id=self.kwargs['hash_id'], parent_comment_id__isnull=True,
            )
            .prefetch_related('likes')
            .annotate(Count('likes'))
            .order_by('-likes__count', '-created_at')
        )

    def get_paginate_by(self, queryset):
        """Return 3 comments by default."""
        return self.request.GET.get('page_size', 3)

    def get_context_data(self, **kwargs):
        """Insert hash_id into the context dict."""
        context = super().get_context_data(**kwargs)
        context['hash_id'] = self.kwargs['hash_id']
        return context


class ApiCommentsListView(CommentsListView):
    def get_queryset(self):
        return (
            Comment.objects.filter(
                entity_content_type_id=self.kwargs['entity_content_type_id'],
                entity_object_id=self.kwargs['entity_object_id'],
                parent_comment_id__isnull=True,
            )
            .prefetch_related('likes')
            .annotate(Count('likes'))
            .order_by('-likes__count', '-created_at')
        )

    def get_paginate_by(self, queryset):
        return '10'

    def serialize_comment(self, comment: Comment):
        serialized_comment = {
            'id': comment.id,
            'user': {
                'name': comment.user.profile.name,
                'username': comment.user.username,
                'url': comment.user.profile.absolute_url,
                'avatar': None,
                'badges': comment.user.profile.serialized_badges,
                'urlRemoveSpam': None,
            },
            'content': markdown_with_parsed_tags_and_shortcodes(comment.content),
            'contentRaw': comment.content,
            'dateCreated': comment.created_at.strftime('%a %d %b, %Y - %H:%M'),
            'dateUpdated': comment.updated_at.strftime('%a %d %b, %Y - %H:%M'),
            'naturalCreationTime': compact_naturaltime(comment.created_at),
            'likesCount': comment.likes.count(),
            'isLiked': comment.is_liked(self.request.user),
            'isOwn': (comment.user.id == self.request.user.id),
            'isEdited': comment.is_edited,
            'isContentAuthor': (comment.user.id == comment.entity.user.id),
            'isAuthorModerator': is_moderator(comment.user),
            'isAuthorAdmin': comment.user.is_staff,
            'likeToggleUrl': comment.like_toggle_url,
            'deleteUrl': reverse('comment_delete', kwargs={'comment_id': comment.id}),
            'editUrl': reverse('comment_edit', kwargs={'comment_id': comment.id}),
            'editAdminUrl': reverse('admin:dillo_comment_change', args=[comment.id]),
            'parentCommentId': (None if not comment.parent_comment else comment.parent_comment.id),
            'urlReport': reverse(
                'report_content',
                kwargs={'content_type_id': comment.content_type_id, 'object_id': comment.id},
            ),
        }

        # Generate thumbnail for user, if available
        if comment.user.profile.avatar:
            serialized_comment['user']['avatar'] = sorl.thumbnail.get_thumbnail(
                comment.user.profile.avatar, '128x128', crop='center', quality=80
            ).url

        # Add replies
        if not comment.parent_comment:
            serialized_comment['replies'] = [
                self.serialize_comment(reply) for reply in comment.replies
            ]

        # Link to remove spam user (only if admin or moderator)
        if (
            self.request.user.groups.filter(name='moderators').exists()
            or self.request.user.is_superuser
        ):
            serialized_comment['user']['urlRemoveSpam'] = reverse(
                'remove-spam-user-embed', kwargs={'pk': comment.user.id}
            )

        return serialized_comment

    def render_to_response(self, context, **response_kwargs):
        comments = []
        for comment in context['comments']:
            # Serialize all objects
            comments.append(self.serialize_comment(comment))

        page_obj = context['page_obj']

        url_next_page = None
        if page_obj.has_next():
            url_next_page = reverse(
                'api-comments-list',
                kwargs={
                    'entity_content_type_id': self.kwargs['entity_content_type_id'],
                    'entity_object_id': self.kwargs['entity_object_id'],
                },
            )
            url_next_page += f"?page={page_obj.next_page_number()}"

        return JsonResponse({'results': comments, 'urlApiCommentListViewNextPage': url_next_page})


@require_POST
@login_required
def comment_create(request):
    """Create a comment for a Post, or a Comment reply."""
    form = forms.CommentForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': form.errors.as_json()}, status=422)

    entity_type = ContentType.objects.get_for_id(form.cleaned_data['entity_content_type_id'])
    entity = entity_type.get_object_for_this_type(id=form.cleaned_data['entity_object_id'])

    comment = Comment.objects.create(
        user=request.user,
        content=form.cleaned_data['content'],
        entity=entity,
        parent_comment_id=form.cleaned_data['parent_comment_id'],
    )

    return JsonResponse(
        {
            'status': 'success',
            'content': render_to_string('dillo/components/_comment_view.pug', {'comment': comment}),
        }
    )


@require_POST
@login_required
def comment_delete(request, comment_id):
    """Delete a comment."""
    comment = get_object_or_404(Comment, pk=comment_id)
    if request.user != comment.user:
        return JsonResponse({'error': 'Not allowed to delete this comment.'}, status=422)

    comment.delete()

    return JsonResponse({'status': 'success'})


@require_POST
@login_required
def comment_edit(request, comment_id):
    """Edit a comment."""
    comment = get_object_or_404(Comment, pk=comment_id)
    if request.user != comment.user and not request.user.is_staff:
        return JsonResponse({'error': 'Not allowed to edit this comment.'}, status=422)

    content = request.POST['content']

    if len(content) < 1:
        return JsonResponse({'error': 'Please type something'}, status=422)

    comment.content = content
    comment.save()

    return JsonResponse(
        {
            'content': markdown_with_parsed_tags_and_shortcodes(comment.content),
            'contentRaw': comment.content,
        }
    )
