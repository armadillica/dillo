import logging

from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import DeleteView
from django.urls import reverse, reverse_lazy

from dillo.models.comments import Comment
from dillo.models.mixins import Likes
from dillo.models.posts import Post


log = logging.getLogger(__name__)


class RemoveSpamUserView(LoginRequiredMixin, DeleteView):
    """Form view for content deletion. Loaded embedded in a modal."""

    template_name = 'dillo/form_remove_spam_user_embed.pug'
    model = User
    success_url = reverse_lazy('remove-spam-user-success-embed')

    def get_context_data(self, **kwargs):
        """Insert the form and url construction data into the context."""
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        context['summary'] = {
            'comments_count': Comment.objects.filter(user=user).count(),
            'likes_count': Likes.objects.filter(user=user).count(),
            'posts': Post.objects.filter(user=user).count(),
        }

        context['last_comments'] = Comment.objects.filter(user=user).order_by('-created_at')[:3]

        context['action_url'] = reverse(
            'remove-spam-user-embed', kwargs={'pk': self.get_object().id},
        )
        context['submit_label'] = "Remove Spam User"
        return context
