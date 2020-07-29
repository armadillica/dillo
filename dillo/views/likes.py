from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from dillo.views.mixins import UserListEmbedView
from dillo.models.mixins import Likes


@require_POST
@login_required
def like_toggle(request, content_type_id, object_id):
    """Toggle Post or Comment like."""
    content_type = ContentType.objects.get_for_id(content_type_id)
    item = get_object_or_404(content_type.model_class(), pk=object_id)
    action, action_label, likes_count, likes_word = item.like_toggle(request.user)
    return JsonResponse(
        {
            'status': 'success',
            'action': action,
            'action_label': action_label,
            # Used to fetch the related element to update the likes count label
            'likes_count_id': f'likes-count-{item.content_type_id}-{item.id}',
            'likes_count': likes_count,
            'likes_word': likes_word,
        }
    )


class LikesListEmbed(UserListEmbedView):
    """List of all likes for an object."""

    def get_queryset(self):
        return Likes.objects.filter(
            content_type_id=self.kwargs['content_type_id'], object_id=self.kwargs['object_id'],
        ).order_by('id')

    # TODO (fsiddi) Consider sorting by creation date (needs to be added)

    def get_users_list(self):
        return [ob.user for ob in self.object_list]
