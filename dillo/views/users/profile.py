import hashlib
import logging
import random
from urllib.parse import urlencode

from actstream.models import Follow
from actstream.actions import follow
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import F
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import DetailView, UpdateView, FormView, View
from taggit.models import Tag

import dillo.models.mixins
import dillo.tasks
import dillo.tasks.storage
from dillo import forms
from dillo.models.posts import get_trending_tags, Post
from dillo.models.profiles import Profile, City
from dillo.views.mixins import PostListEmbedView, OgData, UserListEmbedView

log = logging.getLogger(__name__)


class ProfileDetailView(DetailView):
    """View profile details.

    In order to get a profile we need a User instance. This is why we
    base this view on the User model.
    The idea is to always access the Profile from the User instance.
    """

    model = User
    template_name = 'dillo/profile_details.pug'
    context_object_name = 'user'
    slug_url_kwarg = 'username'
    slug_field = 'username'

    def populate_og_data(self, user):
        """Prepare the OgData object for the context."""
        title = user.username if not user.profile.name else user.profile.name

        image_field = None
        # For image use reel thumbnail
        if user.profile.reel_thumbnail_16_9:
            image_field = user.profile.reel_thumbnail_16_9
        # Otherwise use the avatar
        elif user.profile.avatar:
            image_field = user.profile.avatar
        # Otherwise use the thumbnails of the latest posts
        elif user.post_set.filter(status='published'):
            latest_post = user.post_set.filter(status='published').last()
            if latest_post.thumbnail:
                image_field = latest_post.thumbnail

        image_alt = f"{title} on anima.to"

        return OgData(
            title=title,
            description=user.profile.bio,
            image_field=image_field,
            image_alt=image_alt,
        )

    def dispatch(self, request, *args, **kwargs):
        # Update view count, only every 10th page view in average
        hit_factor = settings.ITEM_HITS_FACTOR
        hit_threshold = 0.1 / hit_factor  # For example 0.01
        # Only if the random number between 0 and 1 is smaller than 0.01
        if (random.random() / hit_factor) < hit_threshold:
            # Add some variety to the count increase by adding or subtracting some
            # random numbers (in average it does not count)
            views_count_increase = hit_factor + random.choice([-3, -1, 1, 3])
            # Increase view count
            Profile.objects.filter(user=self.get_object()).update(
                views_count=F('views_count') + views_count_increase
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query_url'] = reverse(
            'posts_by_user_list', kwargs={'user_id': context['object'].id}
        )
        context['layout'] = 'grid'
        context['og_data'] = self.populate_og_data(context['user'])
        return context


class ProfileUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Profile edit view.

    Makes use of Inline Form Sets. Inspired by https://github.com/zxenia/
    example-inline-formsets/blob/master/mycollections/views.py
    """

    model = Profile
    template_name = 'dillo/profile_edit.pug'
    form_class = forms.ProfileForm
    success_message = 'Profile updated.'

    def get_success_url(self):
        return reverse('profile_edit')

    def get_object(self, queryset=None):
        return self.request.user.profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.get_object().country:
            cities = City.objects.filter(country=self.get_object().country)
            context['form'].fields['city'].widget.choices = [(c.name, c.name) for c in cities]

        if self.request.POST:
            context['links'] = forms.ProfileLinksFormSet(self.request.POST, instance=self.object)
        else:
            context['links'] = forms.ProfileLinksFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        links = context['links']
        with transaction.atomic():
            form.instance.created_by = self.request.user
            self.object = form.save()
            if links.is_valid():
                links.instance = self.object
                links.save()
        return super(ProfileUpdateView, self).form_valid(form)


class PostsByUserListView(PostListEmbedView):
    """All posts created by a User."""

    def get_queryset(self):
        """Filter posts by tag, return 404 if no post is found."""
        return Post.objects.filter(
            user_id=self.kwargs['user_id'], status='published', visibility='public'
        )

    def get_template_names(self):
        return ['dillo/posts_grid_embed.pug']

    def get_paginate_by(self, queryset):
        return 40


class UserFollowersListEmbed(UserListEmbedView):
    """List of all followers for an object."""

    def get_queryset(self):
        return Follow.objects.filter(
            content_type=ContentType.objects.get(model='user'),
            object_id=self.kwargs['user_id'],
        ).order_by('started')

    def get_users_list(self):
        return [ob.user for ob in self.object_list]


class UserFollowingListEmbed(UserListEmbedView):
    """List of all users followed by a user."""

    def get_queryset(self):
        return Follow.objects.filter(
            content_type=ContentType.objects.get(model='user'),
            user_id=self.kwargs['user_id'],
        ).order_by('started')

    def get_users_list(self):
        return [ob.follow_object for ob in self.object_list]


class ProfileSetupTemplateViewMixin(LoginRequiredMixin, View):
    """Base view used for the Profile Setup.

    This view is extended in two ways:
    - by ProfileSetupUpdateViewMixin into a Profile UpdateView
    - by ProfileSetupTags into a FormView
    """

    template_name = 'dillo/profile_setup.pug'
    title = "Let's Set You Up"
    message = ''

    @property
    def next_setup_stage_name(self):
        stages = settings.PROFILE_SETUP_STAGES
        current_stage = self.request.user.profile.setup_stage
        next_stage_index = stages.index(current_stage) + 1
        if next_stage_index >= len(stages):
            log.debug('Profile setup is complete')
            return ''
        log.debug('Profile setup moving to %s' % stages[next_stage_index])
        return stages[next_stage_index]

    def form_valid(self, form):
        profile = self.request.user.profile
        if not self.next_setup_stage_name:
            profile.is_setup_complete = True
        profile.setup_stage = self.next_setup_stage_name
        profile.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('profile_setup')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['message'] = self.message
        return context


class ProfileSetupUpdateViewMixin(ProfileSetupTemplateViewMixin, UpdateView):
    model = Profile

    def get_object(self, queryset=None):
        return self.request.user.profile


class ProfileSetupAvatar(ProfileSetupUpdateViewMixin):
    message = 'Choose an avatar that represents you!\nClick on the image to change it.'
    fields = ['avatar']

    def download_and_assign_gravatar(self, user: User):
        email = user.email
        # TODO(fsiddi) If a plus is found in the email, try to remove it and query Gravatar
        default = "identicon"
        size = 240
        gravatar_url = (
            "https://www.gravatar.com/avatar/"
            + hashlib.md5(email.lower().encode('utf-8')).hexdigest()
            + ".jpg?"
        )
        gravatar_url += urlencode({'d': default, 's': str(size)})

        log.debug("Update profile avatar for user %i" % user.id)
        dillo.tasks.storage.download_image_from_web(gravatar_url, user.profile.avatar)

    def dispatch(self, request, *args, **kwargs):
        # If user does not have an avatar, try to fetch it from Gravatar
        user = request.user
        if not user.profile.avatar:
            self.download_and_assign_gravatar(user)

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Force update avatar."""
        initial = super().get_initial()
        updated_user = Profile.objects.get(user=self.request.user)
        initial['avatar'] = updated_user.avatar
        return initial

    def get_form(self, form_class=None):
        from django.forms import widgets

        form = super().get_form(form_class)
        form.fields['avatar'].label = ''
        form.fields['avatar'].widget = forms.ImageWidget()
        return form


class ProfileSetupBio(ProfileSetupUpdateViewMixin):
    message = 'Tell us a bit more about you.'
    fields = ['bio', 'tags', 'country', 'city', 'reel']

    def get_form(self, form_class=None):
        from django.forms import widgets

        form = super().get_form(form_class)
        form.fields[
            'tags'
        ].help_text = 'Tags that represent you (e.g. animation, rigging, lighting, etc.)'
        form.fields['city'].widget = widgets.Select()
        return form


class ProfileSetupLinks(ProfileSetupUpdateViewMixin):
    template_name = 'dillo/profile_setup_links.pug'
    message = 'Do you have a website? Social media? Add them to your profile!'
    fields = ['website']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['links'] = forms.ProfileLinksFormSet(self.request.POST, instance=self.object)
        else:
            context['links'] = forms.ProfileLinksFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        links = context['links']
        with transaction.atomic():
            form.instance.created_by = self.request.user
            self.object = form.save()
            if links.is_valid():
                links.instance = self.object
                links.save()
        return super().form_valid(form)


class ProfileSetupTags(ProfileSetupTemplateViewMixin, FormView):
    """Allow the user to follow some tags.

    This is done by gathering the most popular tags at the moment, displaying
    them in the template as 'toggles', and pushing their value into a hidden
    field in the ProfileSetupTagsForm as a comma-separated string if the user
    selects any of them. On valid form, we let the user follow those tags.
    """

    template_name = 'dillo/profile_setup_tags.pug'
    message = 'Select the tags that you would like to follow.'
    form_class = forms.ProfileSetupTagsForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['trending_tags'] = get_trending_tags()
        return context

    def form_valid(self, form):
        # Read the tag field value and turn it into a list
        tags_to_follow = form.cleaned_data['tags'].split(',')
        # Strip empty strings
        tags_to_follow = [t for t in tags_to_follow if t]
        for tag_to_follow in tags_to_follow:
            try:
                tag = Tag.objects.get(name=tag_to_follow)
            except Tag.DoesNotExist:
                log.warning("User tried to follow non existing tag %s" % tag_to_follow)
                continue
            follow(self.request.user, tag, actor_only=False)

        return super().form_valid(form)


class ProfileSetup(LoginRequiredMixin, View):
    """Entry point for profile setup.

    Depending on request_user.setup_stage, we return the appropriate view.
    The 'avatar', 'bio', 'links' use a ModelView based view, while the 'tags'
    stage uses a FormView. This is because 'tags' needs dedicated processing.
    More info available in each view.
    """

    def return_view(self, request, *args, **kwargs):
        user_profile = self.request.user.profile
        if user_profile.is_setup_complete:
            return redirect(reverse('homepage'))

        profile_setup_map = {
            'avatar': ProfileSetupAvatar,
            'bio': ProfileSetupBio,
            'links': ProfileSetupLinks,
            'tags': ProfileSetupTags,
        }

        # If the setup stage is not in the list, restart the setup
        if user_profile.setup_stage not in profile_setup_map:
            log.warning('Resetting setup_stage to avatar')
            setup_view_name = 'avatar'
            user_profile.setup_stage = setup_view_name
            user_profile.save()

        view = profile_setup_map[user_profile.setup_stage].as_view()
        return view(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.return_view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.return_view(request, *args, **kwargs)
