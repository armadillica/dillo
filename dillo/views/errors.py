"""Error handlers."""

from django.http import HttpResponse
from django.views.generic import TemplateView
from dillo.views.mixins import OgData


class ErrorView(TemplateView):
    """Renders an error page."""

    # TODO(fsiddi): respond as JSON when this is an XHR.

    status = 500

    def dispatch(self, request=None, *args, **kwargs):
        if request is None or request.method in {'HEAD', 'OPTIONS'}:
            # Don't render templates in this case.
            return HttpResponse(status=self.status)

        # We allow any method for this view,
        response = self.render_to_response(self.get_context_data(**kwargs))
        response.status_code = self.status
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['og_data'] = OgData(
            title='anima.to',
            description='Connecting animators frame by frame.',
            image_field=None,
            image_alt=None,
        )
        return context


def csrf_failure(request, reason=""):
    import django.views.csrf

    return django.views.csrf.csrf_failure(
        request, reason=reason, template_name='errors/403_csrf.pug'
    )
