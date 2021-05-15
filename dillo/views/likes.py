from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import View
import sorl.thumbnail

from dillo.views.mixins import UserListEmbedView
from dillo.models.mixins import Likes, ApiResponseData


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


class ApiUserListLiked(View):
    def get(self, request, content_type_id, object_id):
        """Get the list of user who like an Object."""
        r = ApiResponseData()
        object_query_filter = {'content_type_id': content_type_id, 'object_id': object_id}
        # Build query
        likes = Likes.objects.filter(**object_query_filter).prefetch_related('user').order_by('id')
        # Query to count total number of likes
        r.count = likes.count()
        paginator = Paginator(likes, 15)
        page_number = request.GET.get('page')
        # Query a page worth of likes
        page_obj = paginator.get_page(page_number)
        # If one more page is available, build a url to query it
        r.url_next_page = (
            None
            if not page_obj.has_next()
            else f"{reverse('api-user-list-liked', kwargs=object_query_filter)}"
            f"?page={page_obj.next_page_number()}"
        )
        # Build list of users
        for like in page_obj.object_list:
            u = {
                'name': like.user.profile.name,
                'username': like.user.username,
                'url': like.user.profile.absolute_url,
                'avatar': None,
                'badges': like.user.profile.serialized_badges,
            }
            # Generate thumbnail for user, if available
            if like.user.profile.avatar:
                u['avatar'] = sorl.thumbnail.get_thumbnail(
                    like.user.profile.avatar, '128x128', crop='center', quality=80
                ).url
            r.results.append(u)
        return JsonResponse(r.serialize())
