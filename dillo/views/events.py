import logging
import datetime

from django import forms
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import SuspiciousOperation
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.views import View
from django.views.generic import ListView, DetailView, CreateView

from dillo.models.events import Event
from dillo.views.mixins import OgData

log = logging.getLogger(__name__)


class EventCreateView(LoginRequiredMixin, CreateView):

    template_name = 'dillo/events/event_form.pug'

    model = Event
    fields = [
        'name',
        'location',
        'is_online',
        'description',
        'image',
        'website',
        'starts_at',
        'ends_at',
    ]

    def get_unique_slug(self, name: str) -> str:
        slug = slugify(name)
        counter = 1
        while Event.objects.filter(slug=slug):
            slug = slug + str(counter)
            counter += 1
        return slug

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['starts_at'].widget = forms.TextInput(attrs={'type': 'date'})
        form.fields['ends_at'].widget = forms.TextInput(attrs={'type': 'date'})
        return form

    def form_valid(self, form):
        # Set user as owner of the short
        form.instance.user = self.request.user
        form.instance.visibility = 'unlisted'
        form.instance.slug = self.get_unique_slug(form.instance)
        return super().form_valid(form)


class EventListView(ListView):
    """List of all published events."""

    queryset = Event.objects.filter(visibility='public')
    context_object_name = 'events'
    model = Event
    template_name = 'dillo/events/event_list.pug'

    def get_queryset(self):
        # Show only events that happened yesterday, today or in the future
        yesterday = timezone.now() - datetime.timedelta(days=1)
        return Event.objects.filter(starts_at__gte=yesterday, visibility='public').order_by(
            'starts_at'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['og_data'] = OgData(
            title="Animation Events on anima.to",
            description="Public events in the world of animation.",
            image_field=None,
            image_alt=None,
        )
        return context


class EventDetailView(DetailView):
    """View Event details."""

    context_object_name = 'event'
    template_name = 'dillo/events/event_detail.pug'

    def populate_og_data(self):
        """Prepare the OgData object for the context."""
        event = self.object
        image_field = None if not event.image else event.image

        return OgData(
            title=event.name,
            description=event.description,
            image_field=image_field,
            image_alt=f"{event.name} on anima.to",
        )

    def get_object(self, queryset=None):
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        if event.visibility == 'public' or self.request.user.is_superuser:
            return event
        raise SuspiciousOperation('Someone tried to view unpublished Event %i' % event.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['og_data'] = self.populate_og_data()
        return context


class EventAttendToggle(LoginRequiredMixin, View):
    """Add or remove current user from attendees property"""

    def post(self, request, *args, **kwargs):
        action = self.kwargs['toggle_action']
        # Validate 'action' input
        if action not in {'attend', 'decline'}:
            return JsonResponse({'error': f'action {action} not supported'}, status=422)
        # Fetch the Event or 404
        event = get_object_or_404(Event, slug=self.kwargs['slug'])

        # Process the follow action
        if action == 'attend':
            if self.request.user in event.attendees.all():
                return JsonResponse({'error': f'You are already attending this event'}, status=422)
            log.debug('User %i attends event %s' % (self.request.user.id, event.name))
            event.attendees.add(self.request.user)
        else:  # This must be the 'decline' case
            if self.request.user not in event.attendees.all():
                return JsonResponse({'error': f'You already declined this event'}, status=422)
            event.attendees.remove(self.request.user)
            log.debug('User %i declined event %s' % (self.request.user.id, event.name))
        return JsonResponse({'status': 'success',})
