import copy
import logging

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.http.response import Http404

log = logging.getLogger(__name__)


def deactivate_user_and_remove_content(user: User):
    """Delete user content, but not the user.

    Create a copy of the User, Profile, Account props, then delete the
    user and all its related content (using object.delete(), then
    re-create the user with its profile and account info in a deactivated
    state, to prevent new sign-ups."""

    user_copy = copy.deepcopy(user)
    profile_copy = copy.deepcopy(user.profile)
    account_email_copy = list(EmailAddress.objects.filter(user=user))
    account_social_copy = list(SocialAccount.objects.filter(user=user))
    user.delete()

    log.debug('Deleted user %i' % user_copy.id)
    restored_user = User.objects.create(
        username=user_copy.username,
        email=user_copy.email,
        date_joined=user_copy.date_joined,
        is_active=False,
    )
    restored_user.profile.ip_address = profile_copy.ip_address
    restored_user.profile.save()

    for e in account_email_copy:
        EmailAddress.objects.create(user=restored_user, email=e.email)

    for s in account_social_copy:
        SocialAccount.objects.create(
            user=restored_user,
            provider=s.provider,
            uid=s.uid,
            last_login=s.last_login,
            date_joined=s.date_joined,
            extra_data=s.extra_data,
        )

    log.debug('Restored user in inactive state')


def check_should_content_be_visible(item, requesting_user: User):
    """Check if the current Item should be visible for the requesting_user."""
    if requesting_user.is_superuser:
        return
    if requesting_user.groups.filter(name='moderators').exists():
        return
    if item.status != 'published' and item.user != requesting_user:
        raise Http404
