from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from dillo import forms
from dillo.models.posts import Comment


class CommentsListView(ListView):
    """List of all published comments."""

    context_object_name = 'comments'
    template_name = 'dillo/comments_list.pug'

    def get_queryset(self):
        return (
            Comment.objects.filter(
                post__hash_id=self.kwargs['hash_id'], parent_comment_id__isnull=True
            )
            .prefetch_related('likes')
            .annotate(Count('likes'))
            .order_by('-likes__count', '-created_at')
        )

    def get_paginate_by(self, queryset):
        """Return 3 comments by default."""
        return self.request.GET.get('page_size', 3)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hash_id'] = self.kwargs['hash_id']
        return context


class ApiCommentsListView(CommentsListView):
    def render_to_response(self, context, **response_kwargs):
        comments = []
        for c in context['comments']:
            # Serialize all objects
            comments.append({'user': c.user.username, 'content': c.content})
        return JsonResponse({'results': comments})


@require_POST
@login_required
def comment_create(request):
    """Create a comment for a Post, or a Comment reply."""
    form = forms.CommentForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': form.errors.as_json()}, status=422)

    comment = Comment.objects.create(
        user=request.user,
        content=form.cleaned_data['content'],
        post_id=form.cleaned_data['post_id'],
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
