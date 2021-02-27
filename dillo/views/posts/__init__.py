from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import SuspiciousOperation
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import UpdateView, DetailView
from user_agents import parse

from dillo import forms
from dillo.models.posts import Post
from dillo.views.mixins import OgData


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    fields = ['title']
    template_name = 'dillo/generic_form_embed.pug'

    def get_object(self, queryset=None):
        try:
            return Post.objects.get(hash_id=self.kwargs['hash_id'], user=self.request.user)
        except Post.DoesNotExist:
            raise SuspiciousOperation(
                'User %i tried to edit Post %s' % (self.request.user.id, self.kwargs['hash_id'])
            )

    def get_context_data(self, **kwargs):
        """Insert action_url into the context dict."""
        context = super().get_context_data(**kwargs)
        context['action_url'] = reverse(
            'embed_post_update', kwargs={'hash_id': self.kwargs['hash_id']}
        )
        context['submit_label'] = "Edit Post"
        return context

    def get_success_url(self):
        return reverse('post_update_success_embed', kwargs={'hash_id': self.kwargs['hash_id']})


class PostUpdateSuccessEmbedView(LoginRequiredMixin, DetailView):
    template_name = 'dillo/post_update_success_embed.pug'

    def get_object(self, queryset=None):
        return Post.objects.get(hash_id=self.kwargs['hash_id'])


class PostDetailView(DetailView):
    """View Post details.

    Comments are loaded asynchronously.
    """

    context_object_name = 'post'

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        """Force the creation of CSRF cookie"""
        return super().dispatch(*args, **kwargs)

    def get_related_posts(self, post):
        return (
            Post.objects.filter(user=post.user)
            .exclude(id=post.id)
            .prefetch_related('likes')
            .annotate(Count('likes'))
            .order_by('-likes__count', '-created_at')[:6]
        )

    def populate_og_data(self, post):
        """Prepare the OgData object for the context."""
        title = post.user.username if not post.user.profile.name else post.user.profile.name

        image_field = None
        if post.thumbnail:
            image_field = post.thumbnail
        # Otherwise use the avatar
        elif post.user.profile.avatar:
            image_field = post.user.profile.avatar

        return OgData(
            title=title,
            description=post.title,
            image_field=image_field,
            image_alt=f"{title} on anima.to",
        )

    def get_object(self, queryset=None):
        post = get_object_or_404(Post, hash_id=self.kwargs['hash_id'])
        user = self.request.user
        if post.status == 'published' and post.visibility == 'public' or user.is_superuser:
            return post
        elif post.status != 'published':
            if user.is_authenticated and post.user == user:
                return post
        raise SuspiciousOperation(
            'Someone tried to view an unpublished Post from User %i' % post.user.id
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_comment'] = forms.CommentForm({'post_id': self.object.id})
        context['og_data'] = self.populate_og_data(kwargs['object'])
        context['related_posts'] = self.get_related_posts(self.object)
        return context

    def get_template_names(self):
        ua_string = self.request.headers.get('user-agent', '')
        user_agent = parse(ua_string)
        if self.request.is_ajax():
            # Embedded post detail (desktop version)
            template = 'list_media'
            if user_agent.is_mobile and self.request.GET.get('from_post_detail'):
                # Embedded post detail (mobile, with media)
                template = 'slick_media'
            elif user_agent.is_mobile:
                # Embedded post detail from post list (mobile, no media - comments only)
                template = 'base'
            return f'dillo/post_detail_embed_{template}.pug'
        else:
            return 'dillo/post_detail.pug'


@require_POST
@login_required
def post_delete(request, hash_id):
    """Delete a Post."""
    post = get_object_or_404(Post, hash_id=hash_id)
    if request.user != post.user:
        raise SuspiciousOperation(
            'User %i tried to delete a Post from User %i' % (request.user.id, post.user.id)
        )
    post.delete()
    # TODO(fsiddi) Delete related activities
    return JsonResponse({'status': 'success'})
