import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.urls import reverse
from django.views.generic import FormView

from dillo import forms, tasks
from dillo.models.messages import ContentReports

log = logging.getLogger(__name__)


class ReportContentView(LoginRequiredMixin, FormView):
    """Form view for content reporting. Loaded embedded in a modal."""

    template_name = 'dillo/generic_form_embed.pug'
    form_class = forms.ReportContentForm

    def get_reported_content(self):
        """Utility to verify that the requested content exists."""
        content_type = ContentType.objects.get(pk=self.kwargs['content_type_id'])
        try:
            content = content_type.get_object_for_this_type(pk=self.kwargs['object_id'])
        except ObjectDoesNotExist:
            log.error(
                "%s not found for id %i"
                % (content_type.name.capitalize(), self.kwargs['object_id'])
            )
            raise Http404("Not found")
        return content

    def get_success_url(self):
        return reverse('report_content_success_embed')

    def form_valid(self, form):
        """Generate a ContentReport and schedule an email notification."""
        content = self.get_reported_content()
        log.info("Creating content report (%s)" % form.cleaned_data['reason'])
        report = ContentReports.objects.create(
            user=self.request.user,
            content_object=content,
            reason=form.cleaned_data['reason'],
            notes=form.cleaned_data['notes'],
        )
        tasks.send_mail_report_content(report.id)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Insert the form and url construction data into the context dict."""
        context = super().get_context_data(**kwargs)
        if 'form' not in context:
            context['form'] = self.get_form()

        content = self.get_reported_content()
        context['action_url'] = reverse(
            'report_content',
            kwargs={'content_type_id': content.content_type_id, 'object_id': content.id},
        )
        context['submit_label'] = "Report Content"
        return context
