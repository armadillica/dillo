from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from dillo.models.comments import Comment
from dillo.tasks.emails import send_notification_mail
from dillo.tests.factories.users import UserFactory
from dillo.tests.factories.posts import PostFactory


@override_settings(STATICFILES_STORAGE='pipeline.storage.PipelineStorage')
class EmailNotificationTest(TestCase):
    def setUp(self) -> None:
        self.user_harry = UserFactory(username='harry')
        self.user_hermione = UserFactory(username='hermione')
        self.post = PostFactory(
            user=self.user_harry, status='published', title='Velocità con #animato'
        )
        self.client = Client()

    def test_notification_with_no_valid_template(self):
        send_notification_mail('Fail mail', self.user_harry, 'invalid', context={})
        self.assertEqual(len(mail.outbox), 0)

    def test_like_post_email_notification(self):
        like_toggle_url = reverse(
            'like_toggle',
            kwargs={'content_type_id': self.post.content_type_id, 'object_id': self.post.id},
        )
        # Log in the user.
        self.client.force_login(self.user_hermione)
        # Toggle a like.
        self.client.post(like_toggle_url)

        # Test that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)

        # Verify that the subject of the first message is correct.
        self.assertEqual(mail.outbox[0].subject, 'Your post has a new like!')
        # print(mail.outbox[0].alternatives[0][0])

    def test_new_comment_notification(self):
        self.client.force_login(self.user_hermione)
        comment_create_url = reverse('comment_create')
        comment_form_content = {
            'entity_object_id': self.post.id,
            'entity_content_type_id': self.post.content_type_id,
            'content': 'Interesting content!',
        }
        self.client.post(comment_create_url, comment_form_content)

        # Test that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)

        # Verify that the subject of the first message is correct.
        self.assertEqual(mail.outbox[0].subject, 'Your post "Velocità con #…" has a new comment')
        # print(mail.outbox[0].alternatives[0][0])

    def test_new_reply_notification(self):
        comment_create_url = reverse('comment_create')
        comment_form_content = {
            'entity_object_id': self.post.id,
            'entity_content_type_id': self.post.content_type_id,
            'content': 'Interesting content!',
        }
        # Login as Hermione.
        self.client.force_login(self.user_hermione)
        # Add comment to existing post.
        self.client.post(comment_create_url, comment_form_content)
        # Empty the test outbox.
        mail.outbox = []
        # Ensure only one comment for this posts exists.
        self.assertEqual(self.post.comments.count(), 1)

        # Get the comment.
        comment = Comment.objects.get(
            entity_content_type_id=self.post.content_type_id, entity_object_id=self.post.id
        )

        # Build a reply object.
        reply_form_content = {
            'entity_object_id': self.post.id,
            'entity_content_type_id': self.post.content_type_id,
            'parent_comment_id': comment.id,
            'content': 'Interesting content!',
        }
        self.client.force_login(self.user_harry)
        self.client.post(comment_create_url, reply_form_content)

        # Test that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)

        # Ensure that the subject is correct.
        self.assertEqual(mail.outbox[0].subject, 'Your comment has a new reply!')
        # print(mail.outbox[0].alternatives[0][0])

    def test_follow_notification(self):
        from actstream.actions import follow

        # Harry follows Hermione
        follow(self.user_harry, self.user_hermione, actor_only=False)

        # Test that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)

        # Ensure that the subject is correct.
        self.assertEqual(mail.outbox[0].subject, 'You have a new follower!')
        # print(mail.outbox[0].alternatives[0][0])
