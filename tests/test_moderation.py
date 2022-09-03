from django.test import TestCase
from django.contrib.auth.models import User

from dillo.models.moderation import SpamWord, AllowedDomain
from dillo.models.posts import Post

from dillo.moderation import deactivate_user_and_remove_content
from dillo.tests.factories.users import UserFactory
from dillo.tests.factories.posts import PostFactory


class ProfileModelTest(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth.models import User

        self.username = 'testuser'
        self.user: User = UserFactory(username=self.username)
        self.user.profile.ip_address = '127.0.0.1'
        self.user.profile.save()

    def test_moderation_delete_user(self):
        deleted_user_id = self.user.id
        deactivate_user_and_remove_content(self.user)
        inactive_user = User.objects.get(username=self.username)

        self.assertFalse(inactive_user.id == deleted_user_id)
        self.assertFalse(inactive_user.is_active)
        self.assertEqual(inactive_user.profile.ip_address, '127.0.0.1')

    # TODO: test for more data:
    #   - Posts, comments, likes
    #   - SocialAccount


class DetectSpamWords(TestCase):
    def test_spam_words(self) -> None:
        for bw in {'bad', 'very bad', 'bad word'}:
            SpamWord.objects.create(word=bw)
        p: Post = PostFactory(title='Looking for #animato')
        self.assertFalse(p.has_spam)

        p: Post = PostFactory(title='Looking for bad')
        self.assertTrue(p.has_spam)

        p: Post = PostFactory(title='Looking for badthings')
        self.assertTrue(p.has_spam)

        p: Post = PostFactory(title='Looking for very badthings')
        self.assertTrue(p.has_spam)

        p: Post = PostFactory(title='Looking for BAD')
        self.assertTrue(p.has_spam)

    def test_spam_links(self):

        p = PostFactory(title='Looking for blender.org')
        self.assertFalse(p.has_spam)

        for url in {'blender.org', 'github.com', 'blender.community'}:
            AllowedDomain.objects.create(url=url)

        p = PostFactory(title='Looking for blender.org')
        self.assertFalse(p.has_spam)

        p = PostFactory(title='Looking for blender.community')
        self.assertFalse(p.has_spam)

        p = PostFactory(title='Looking for blender.com')
        self.assertTrue(p.has_spam)

        p = PostFactory(title='Looking for blender.test')
        self.assertFalse(p.has_spam)

        p = PostFactory(title='Looking for https://blender.test')
        self.assertFalse(p.has_spam)

        p = PostFactory(title='Looking for https://blender.com')
        self.assertTrue(p.has_spam)
