import logging
from django import forms
from django.core.exceptions import ValidationError
from django.core import validators
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

import dillo.models
import dillo.models.profiles
from allauth.account.forms import SignupForm, BaseSignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm


log = logging.getLogger(__name__)


class ImageWidget(forms.ClearableFileInput):
    """Overrides the ClearableFileInput template_name.

    This way we can display an preview of the image, if available.
    """

    template_name = 'dillo/components/_image_input.html'


class PostForm(forms.Form):
    post_id = forms.IntegerField(widget=forms.HiddenInput())
    title = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': _('Write a caption...'),
                'rows': 3,
            }
        ),
        localize=True,
    )


class CommentForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'placeholder': _('Write a comment...'), 'rows': 2,}
        ),
        localize=True,
    )
    entity_content_type_id = forms.IntegerField(widget=forms.HiddenInput())
    entity_object_id = forms.IntegerField(widget=forms.HiddenInput())
    parent_comment_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = dillo.models.profiles.Profile
        fields = ('name', 'bio', 'location', 'avatar', 'website', 'reel')
        widgets = {
            'avatar': ImageWidget,
        }


class ProfileLinksForm(forms.ModelForm):
    """Links Form, used to generate an inline forms set."""

    class Meta:
        models = dillo.models.profiles.ProfileLinks
        exclude = ('social',)


# Inline Form Set that is used in dillo.views.ProfileUpdateView
ProfileLinksFormSet = forms.inlineformset_factory(
    dillo.models.profiles.Profile,
    dillo.models.profiles.ProfileLinks,
    form=ProfileLinksForm,
    max_num=4,
    extra=1,
)


class ReportContentForm(forms.Form):
    """Form to report Posts or Comments."""

    REASONS = (
        ('inappropriate', 'Inappropriate'),
        ('copyright', 'Copyright Infringement'),
        ('other', 'Other'),
    )
    reason = forms.ChoiceField(choices=REASONS)
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}), required=False, label='Additional Notes'
    )


class ContactForm(forms.Form):
    """Form to get in touch or give feedback."""

    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label='Message')


def validate_is_delete(value: str):
    if value != "DELETE":
        raise ValidationError(
            _('"%(value)s" is not "DELETE"'), params={'value': value},
        )


class DeactivateUserForm(forms.Form):
    """Simple form to deactivate a User account."""

    confirm_deletion = forms.CharField(
        help_text="Once deleted, your account can not be recovered.",
        label="Type DELETE to confirm the deletion of your account",
        validators=[validate_is_delete],
    )


# This validator is also used in the signup form, and is included in the
# definition of ACCOUNT_USERNAME_VALIDATORS
custom_username_validators = [validators.validate_unicode_slug]


class AccountUpdateUsernameForm(forms.Form):
    """Simple form to set a valid username."""

    username = forms.CharField(
        label="Change your username",
        help_text="Changing your username will break previous links to your profile.",
        validators=custom_username_validators,
    )

    def clean(self):
        cleaned_data = super().clean()
        if not self.is_valid():
            return
        if User.objects.filter(username=cleaned_data['username']).exists():
            raise forms.ValidationError(
                "The username '%s' is already used, please pick another "
                "one." % cleaned_data['username']
            )


class CustomSignupMixin(BaseSignupForm):
    name = forms.CharField(label="Your Name", empty_value="Your Name",)
    field_order = ['name', 'email', 'password1']

    def save(self, request):
        user = super().save(request)
        cleaned_data = super().clean()
        # Process form again, get the full "Name" and add it to user.profile
        user.profile.name = cleaned_data.get('name')
        user.profile.save()
        log.debug("Create user profile for %s" % user.profile.name)

        # Generate a user profile starting from the profile.name
        username_space_strip = user.profile.name.replace(" ", "")
        username = slugify(username_space_strip)
        counter = 1
        while User.objects.filter(username=username):
            username = username + str(counter)
            counter += 1
        user.username = username
        user.save()
        log.debug("Updated username to %s" % user.username)
        return user


class CustomSignupForm(CustomSignupMixin, SignupForm):
    """Signup Form requiring to accept terms."""


class CustomSocialSignupForm(CustomSignupMixin, SocialSignupForm):
    """Social Signup Form requiring to accept terms."""


class ProfileSetupTagsForm(forms.Form):
    tags = forms.CharField(widget=forms.HiddenInput(), required=False)


class AttachS3UploadToPostForm(forms.Form):
    """Form called from AJAX request."""

    post_id = forms.IntegerField()
    key = forms.CharField()
    name = forms.CharField()
    mime_type = forms.CharField()
    size_bytes = forms.IntegerField()
