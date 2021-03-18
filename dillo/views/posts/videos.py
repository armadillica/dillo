from django.db.models import F
from django.http import JsonResponse
from django.views import View

from dillo.models.posts import Video


class VideoViewsCountIncreaseView(View):
    def post(self, request, *args, **kwargs):
        Video.objects.filter(static_asset_id=self.kwargs['video_id']).update(
            views_count=F('views_count') + 1
        )
        return JsonResponse({'status': 'ok'})
