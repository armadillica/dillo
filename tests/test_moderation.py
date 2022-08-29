from django.test import TestCase
from django.contrib.auth.models import User
from dillo.tests.factories.users import UserFactory

from dillo.moderation import deactivate_user_and_remove_content


class ProfileModelTest(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth.models import User

        self.username = 'testuser'
        self.user: User = UserFactory(username=self.username)

    def test_moderation_delete_user(self):
        deleted_user_id = self.user.id
        deactivate_user_and_remove_content(self.user)
        inactive_user = User.objects.get(username=self.username)

        self.assertFalse(inactive_user.id == deleted_user_id)
        self.assertFalse(inactive_user.is_active)

    # TODO: test for more data:
    #   - Posts, comments, likes
    #   - SocialAccount
