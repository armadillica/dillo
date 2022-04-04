import tempfile
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, Client, override_settings
from django.urls import reverse

import dillo.models
import dillo.models.events
import dillo.models.feeds

from dillo.models.messages import ContentReports
from dillo.models.posts import Post
from dillo.models.comments import Comment
from dillo.models.profiles import Profile
from dillo.tests.factories.users import UserFactory
from dillo.tests.factories.comments import CommentForPostFactory
from dillo.tests.factories.posts import PostFactory


class TestViewsMixin(TestCase):
    def setUp(self) -> None:
        self.user1: User = UserFactory(username='user1')
        self.user2: User = UserFactory(username='user2')
        self.client = Client()


@override_settings(STATICFILES_STORAGE='pipeline.storage.PipelineStorage')
class PostViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory(username='testuser')
        self.post_title = 'Velocità con #animato'
        self.post = Post.objects.get(pk=PostFactory(user=self.user, title=self.post_title).pk)

    def test_existing_post_view(self):
        self.post.status = 'published'
        self.post.save()
        # Create post URL
        post_view_url = reverse('post_detail', kwargs={'hash_id': self.post.hash_id})
        # Issue a GET request
        response = self.client.get(post_view_url)
        # Check that the response is 200 OK
        self.assertEqual(response.status_code, 200)
        # Check that the title of the Post matches with the original title
        self.assertEqual(response.context['post'].title, self.post_title)

    def test_unpublished_post_view(self):
        # Create post URL
        post_view_url = reverse('post_detail', kwargs={'hash_id': self.post.hash_id})
        # Issue a GET request
        response = self.client.get(post_view_url)
        # Check that the response is 400 Not Allowed
        self.assertEqual(response.status_code, 400)
        self.client.force_login(self.user)
        response = self.client.get(post_view_url)
        # Check that the response is 200 OK
        self.assertEqual(response.status_code, 200)

    def test_non_existing_post_view(self):
        from hashid_field import Hashid

        non_existing_post_id = 99
        hash_id = Hashid(non_existing_post_id).hashid
        # Ensure that Post with ID 99 does not exist
        with self.assertRaises(Post.DoesNotExist):
            Post.objects.get(hash_id=hash_id)
        # Create url for non-existing post
        post_view_url = reverse('post_detail', kwargs={'hash_id': hash_id})
        # Issue a GET request
        response = self.client.get(post_view_url)
        # Check that the response is 404
        self.assertEqual(response.status_code, 404)

    def test_post_create_view(self):
        post_create_url = reverse('post_create')
        # Ensure that the view is not available if anonymous
        response = self.client.get(post_create_url)
        self.assertEqual(response.status_code, 302)
        # Log in the user
        self.client.force_login(self.user)
        # Create a Post
        response = self.client.get(post_create_url)
        self.assertEqual(response.status_code, 200)
        # Ensure Post is in the database
        self.assertEqual(1, Post.objects.count())

        # TODO(fsiddi): Test submission of invalid form

    def test_report_post(self):
        report_content_url = reverse(
            'report_content',
            kwargs={'content_type_id': self.post.content_type_id, 'object_id': self.post.id},
        )
        # Ensure that the view is not available if anonymous
        response = self.client.get(report_content_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(0, ContentReports.objects.count())
        random_user = UserFactory()
        # Log in the user
        self.client.force_login(random_user)
        # Create a Post
        self.client.post(report_content_url, {'reason': 'inappropriate'})
        self.assertEqual(1, ContentReports.objects.count())

    def test_post_status(self):
        post_status_url = reverse('post_status', kwargs={'hash_id': self.post.hash_id})
        response = self.client.get(post_status_url)
        self.assertEqual(302, response.status_code)
        self.client.force_login(self.user)
        response = self.client.get(post_status_url)
        self.assertJSONEqual(response.content, {'status': 'draft'})

    @override_settings(
        MEDIA_ROOT=tempfile.TemporaryDirectory(prefix='animato_test').name,
        DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
    )
    def test_post_upload_video_local(self):
        import os

        # Create post URL
        post_file_upload_url = reverse('post_file_upload', kwargs={'hash_id': self.post.hash_id})

        # Build file path
        this_dir = os.path.dirname(os.path.abspath(__file__))
        path_square_video = os.path.join(this_dir, 'upload_test_files/square_video.mp4')
        # Ensure anonymous upload is not allowed

        with open(path_square_video, 'rb') as video_file:
            response = self.client.post(post_file_upload_url, {'file': video_file})
            self.assertEqual(response.status_code, 302)

        # Log in the user
        self.client.force_login(self.user)
        with open(path_square_video, 'rb') as video_file:
            response = self.client.post(post_file_upload_url, {'file': video_file})
            self.assertEqual(response.status_code, 200)

        # Ensure that a video has been attached to the post
        self.assertEqual(1, len(self.post.videos))
        # Ensure that the framerate of the video has been added in the database
        self.assertEqual(24, self.post.videos[0].framerate)

        # Modify settings to prevent videos lasting more than 5 sec to be uploaded
        settings.MEDIA_UPLOADS_VIDEO_MAX_DURATION_SECONDS = 5
        with open(path_square_video, 'rb') as video_file:
            response = self.client.post(post_file_upload_url, {'file': video_file})
            self.assertEqual(response.status_code, 422)

    @override_settings(MEDIA_ROOT=tempfile.TemporaryDirectory(prefix='animato_test').name)
    def test_post_upload_video_s3(self):
        """Test the endpoint called after a file is uploade on s3"""
        post_title = 'Velocità con #animato'
        # Create Post
        entity = Post.objects.create(user=self.user, title=post_title)

        # Create post URL
        attach_url = reverse('attach_s3_upload_to_post')
        # Log in the user
        self.client.force_login(self.user)
        # Attempt a GET request, which is not allowed
        r = self.client.get(attach_url)
        self.assertEqual(r.status_code, 405)

        payload = {
            'entity_id': entity.id,
            'content_type_id': entity.content_type_id,
            'key': '8f/8f8f0ef2516ca5d7699fc1cf27531c35/8f8f0ef2516ca5d7699fc1cf27531c35.MOV',
            'size_bytes': 31534525,
            'name': 'IMG_2372.MOV',
            'mime_type': 'video/quicktime',
        }
        self.client.post(attach_url, payload)
        # Ensure that a video file is attached to the post
        media_video = entity.videos[0]
        self.assertEqual(
            '8f/8f8f0ef2516ca5d7699fc1cf27531c35/8f8f0ef2516ca5d7699fc1cf27531c35.MOV',
            media_video.static_asset.source,
        )
        self.assertEqual(
            'IMG_2372.MOV',
            media_video.static_asset.source_filename,
        )


@override_settings(STATICFILES_STORAGE='pipeline.storage.PipelineStorage')
class CommentViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.post = PostFactory(user=self.user)
        self.comment = CommentForPostFactory(entity=self.post, user=self.user)

    def test_comment_create(self):
        comment_create_url = reverse('comment_create')
        comment_form_content = {
            'entity_object_id': self.post.id,
            'entity_content_type_id': self.post.content_type_id,
            'content': 'Interesting content!',
        }
        # Non-authenticated creation of comments is not allowed
        response = self.client.post(comment_create_url, comment_form_content)
        self.assertEqual(response.status_code, 302)
        # Log in the user
        self.client.force_login(self.user)
        response = self.client.post(comment_create_url, comment_form_content)
        self.assertEqual(response.status_code, 200)
        # Submitting a Comment with no is not allowed
        comment_form_content_no_content = {'post_id': self.post.id}
        response = self.client.post(comment_create_url, comment_form_content_no_content)
        self.assertEqual(response.status_code, 422)

    def test_comment_delete(self):
        comment_delete_url = reverse('comment_delete', kwargs={'comment_id': self.comment.id})
        # Create another user
        other_user = UserFactory()
        self.client.force_login(other_user)
        response = self.client.post(comment_delete_url)
        # Deleting the post is not allowed, because the post belongs to another user
        self.assertEqual(response.status_code, 422)
        # Log in the user who create the post
        self.client.force_login(self.user)
        response = self.client.post(comment_delete_url)
        # Deletion is successful
        self.assertEqual(response.status_code, 200)

    def test_comment_delete_non_existent(self):
        non_existing_comment_id = 2
        with self.assertRaises(Comment.DoesNotExist):
            Comment.objects.get(pk=non_existing_comment_id)
        comment_delete_url = reverse(
            'comment_delete', kwargs={'comment_id': non_existing_comment_id}
        )
        # Log in the default user
        self.client.force_login(self.user)
        response = self.client.post(comment_delete_url)
        # Deletion fails
        self.assertEqual(response.status_code, 404)


@override_settings(STATICFILES_STORAGE='pipeline.storage.PipelineStorage')
class AccountViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.comment = CommentForPostFactory(user=self.user)
        self.post = PostFactory(user=self.user)

    def test_account_delete(self):
        account_delete_url = reverse('account_delete')
        # Non-authenticated creation of comments is not allowed
        response = self.client.post(account_delete_url)
        self.assertEqual(response.status_code, 302)
        # Log in the user
        self.client.force_login(self.user)
        response = self.client.post(account_delete_url, data={'confirm_deletion': '_DELETE'})
        self.assertFormError(response, 'form', 'confirm_deletion', '"_DELETE" is not "DELETE"')
        self.assertEqual(response.status_code, 200)
        response = self.client.post(account_delete_url, data={'confirm_deletion': 'DELETE'})
        self.assertEqual(response.status_code, 302)

        with self.assertRaises(Post.DoesNotExist):
            Post.objects.get(pk=self.post.id)

        with self.assertRaises(Comment.DoesNotExist):
            Comment.objects.get(pk=self.comment.id)

        with self.assertRaises(User.DoesNotExist):
            User.objects.get(pk=self.user.id)

    def test_account_username_update(self):
        account_username_update = reverse('account_update_username')
        # Non-authenticated creation of comments is not allowed
        response = self.client.post(account_username_update)
        self.assertEqual(response.status_code, 302)
        # Log in the user
        self.client.force_login(self.user)
        response = self.client.post(account_username_update, data={'username': ''})
        self.assertFormError(response, 'form', 'username', 'This field is required.')
        self.assertEqual(response.status_code, 200)
        # Correctly update the username
        response = self.client.post(account_username_update, data={'username': 'harry'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.get(pk=self.user.id).username, 'harry')


class NotificationViewsTest(TestViewsMixin):
    def setUp(self):
        super().setUp()
        self.post = PostFactory(user=self.user1, title='Velocità con #animato')
        self.post.refresh_from_db()

    def test_notification_feed_view(self):
        # Ensure that anonymous access is not allowed
        response = self.client.get(reverse('notifications'))
        self.assertEqual(response.status_code, 302)
        # TODO(fsiddi) ensure that redirect url is correct
        # Ensure that notifications are listed
        self.client.force_login(self.user1)
        response = self.client.get(reverse('notifications'))
        self.assertEqual(len(response.context['notifications']), 0)
        # Generate one like activity
        self.post.like_toggle(self.user2)
        response = self.client.get(reverse('notifications'))
        # Ensure that one notification is found
        self.assertEqual(len(response.context['notifications']), 1)

    def test_mark_as_read(self):
        mark_as_read_url = reverse('api-notifications-mark-all-as-read')
        # Ensure that anonymous access is not allowed
        response = self.client.post(mark_as_read_url)
        self.assertEqual(response.status_code, 302)
        # Ensure that GET is not allowed
        self.client.force_login(self.user1)
        response = self.client.get(mark_as_read_url)
        self.assertEqual(response.status_code, 405)

        # Generate one like activity
        self.post.like_toggle(self.user2)

        # Ensure that we have one unread notification
        notifications_count = dillo.models.feeds.FeedEntry.objects.filter(
            user=self.user1,
            category='notification',
            is_read=False,
        ).count()
        self.assertEqual(notifications_count, 1)

        # Perform POST request
        response = self.client.post(mark_as_read_url)
        # Ensure response in 'success'
        self.assertJSONEqual(response.content, {'status': 'success'})

        # Check that unread notifications count is 0
        notifications_count = dillo.models.feeds.FeedEntry.objects.filter(
            user=self.user1,
            category='notification',
            is_read=False,
        ).count()
        self.assertEqual(notifications_count, 0)


@override_settings(STATICFILES_STORAGE='pipeline.storage.PipelineStorage')
class EventViewsTest(TestCase):
    def setUp(self) -> None:
        from django.utils import timezone

        self.user1 = User.objects.create_user(username='testuser1', password='12345')
        self.user2 = User.objects.create_user(username='testuser2', password='12345')
        self.post = dillo.models.posts.Post.objects.create(
            user=self.user1, title='Velocità con #animato'
        )
        self.event = dillo.models.events.Event.objects.create(
            user=self.user1,
            name='Lightbox',
            slug='lightbox',
            website='https://example.com',
            starts_at=timezone.now(),
            ends_at=timezone.now(),
        )
        self.client = Client()

    def test_attend_event(self):
        # Ensure that anonymous user is not allowed
        response = self.client.get(reverse('event_attend_toggle', args=['lightbox', 'follow']))
        self.assertEqual(response.status_code, 302)
        # Ensure the event has no followers
        self.assertFalse(self.event.attendees.all())
        self.client.force_login(self.user1)
        # Ensure that GET is not allowed
        response = self.client.get(reverse('event_attend_toggle', args=['lightbox', 'follow']))
        self.assertEqual(response.status_code, 405)
        # Try POST request, with invalid action argument
        response = self.client.post(reverse('event_attend_toggle', args=['lightbox', 'follow']))
        self.assertEqual(response.status_code, 422)
        # Try POST request, with invalid slug argument
        response = self.client.post(reverse('event_attend_toggle', args=['missing', 'attend']))
        self.assertEqual(response.status_code, 404)
        # Try POST request, with valid arguments
        response = self.client.post(reverse('event_attend_toggle', args=['lightbox', 'attend']))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.user1, self.event.attendees.all())
        # Try POST again on the same event
        response = self.client.post(reverse('event_attend_toggle', args=['lightbox', 'attend']))
        self.assertEqual(response.status_code, 422)
        self.assertIn(self.user1, self.event.attendees.all())
        # Try to decline the event (we are attending it)
        response = self.client.post(reverse('event_attend_toggle', args=['lightbox', 'decline']))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.user1, self.event.attendees.all())


@override_settings(STATICFILES_STORAGE='pipeline.storage.PipelineStorage')
class BookmarkPostViewTest(TestCase):
    def setUp(self) -> None:

        self.user1 = User.objects.create_user(username='testuser1', password='12345')
        self.user2 = User.objects.create_user(username='testuser2', password='12345')
        self.post = dillo.models.posts.Post.objects.create(
            user=self.user1, title='Velocità con #animato'
        )
        self.client = Client()

    def test_bookmarks_post(self):
        response = self.client.post(reverse('bookmark_toggle', args=[self.post.id]))
        # Ensure that anonymous users can't bookmark
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.user1)
        non_existing_post_id = 99
        with self.assertRaises(dillo.models.posts.Post.DoesNotExist):
            dillo.models.posts.Post.objects.get(pk=non_existing_post_id)
        response = self.client.post(reverse('bookmark_toggle', args=[non_existing_post_id]))
        self.assertEqual(response.status_code, 404)

        # Add to bookmarks successfully
        response = self.client.post(reverse('bookmark_toggle', args=[self.post.id]))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'action': 'added', 'status': 'success'})
        self.assertEqual(self.user1.profile.bookmarks.count(), 1)

        # Remove from bookmarks successfully
        response = self.client.post(reverse('bookmark_toggle', args=[self.post.id]))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'action': 'removed', 'status': 'success'})
        self.assertEqual(self.user1.profile.bookmarks.count(), 0)


@override_settings(STATICFILES_STORAGE='pipeline.storage.PipelineStorage')
@override_settings(MEDIA_ROOT=tempfile.TemporaryDirectory(prefix='animato_test').name)
class TheaterReelsViewTest(TestViewsMixin):
    def test_invalid_profile(self):
        """Return 404 if profile does not exist."""
        non_existing_user_id = 999
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=non_existing_user_id)
        response = self.client.get(reverse('reel-detail', args=[non_existing_user_id]))
        # Ensure that anonymous users can't bookmark
        self.assertEqual(response.status_code, 404)

    def test_profile_no_reel(self):
        """Return 404 if profile has no reel."""
        response = self.client.get(reverse('reel-detail', args=[self.user1.id]))
        # Ensure that anonymous users can't bookmark
        self.assertEqual(response.status_code, 404)

    def test_detail_view_pagination(self):
        """Ensure prev_profile and next_profile are correct."""

        def ensure_correct_pagination():
            """The actual test to see if content is paginated properly."""
            # Fetch users, sorted by likes_count (as written in usernames_and_likes_count)
            users = User.objects.exclude(profile__reel__exact='').order_by(
                '-profile__likes_count', 'id'
            )
            users_count = len(users)
            # for user in users:
            #     print(f"({user.id}) {user.username}: {user.profile.likes_count}")
            for user in users:
                # Fetch the reel-detail view
                # print("Fetching", user.username, user.profile.likes_count)
                response = self.client.get(reverse('reel-detail', args=[user.id]))
                idx = list(users).index(user)
                if idx == 0:
                    # We are at the beginning of the list, no prev_profile
                    # print("\tprev_profile_url: None")
                    self.assertIsNone(response.context['prev_profile_url'])
                    expected_next_profile_url = reverse(
                        'reel-detail', kwargs={'profile_id': users[idx + 1].id}
                    )
                    # print(f"\tnext_profile_url: {expected_next_profile_url}")
                    self.assertEqual(
                        response.context['next_profile_url'], expected_next_profile_url
                    )
                elif idx == users_count - 1:
                    # We reached the last user of the query, no next_profile
                    self.assertIsNone(response.context['next_profile_url'])
                else:
                    expected_prev_profile_url = reverse(
                        'reel-detail', kwargs={'profile_id': users[idx - 1].id}
                    )
                    # print(f"\tprev_profile_url: {expected_prev_profile_url}")
                    self.assertEqual(
                        response.context['prev_profile_url'], expected_prev_profile_url
                    )
                    expected_next_profile_url = reverse(
                        'reel-detail', kwargs={'profile_id': users[idx + 1].id}
                    )
                    # print(f"\tnext_profile_url: {expected_next_profile_url}")
                    self.assertEqual(
                        response.context['next_profile_url'], expected_next_profile_url
                    )

        usernames_and_likes_count = [
            ('ron', 10),
            ('hermione', 10),
            ('ginny', 10),
            ('luna', 10),
            ('neville', 10),
        ]

        # Create users and profiles from the list
        for u in usernames_and_likes_count:
            user = User.objects.create_user(username=u[0])
            Profile.objects.filter(user=user).update(
                reel='_some_reel_',
                likes_count=u[1],
            )

        ensure_correct_pagination()

        updated_likes_count = [
            ('luna', 0),
            ('ron', 1),
            ('ginny', 5),
            ('hermione', 10),
            ('neville', 30),
        ]

        for u in updated_likes_count:
            user = User.objects.get(username=u[0])
            Profile.objects.filter(user=user).update(likes_count=u[1])

        ensure_correct_pagination()


@override_settings(STATICFILES_STORAGE='pipeline.storage.PipelineStorage')
class SignUpViewTest(TestCase):
    fixtures = ['socialapps.json']

    def setUp(self) -> None:
        self.client = Client()

    def test_signup_view_invalid_form(self):
        account_signup_url = reverse('account_signup')
        account_signup_form_content = {
            'name': 'Albus Dumbledore',
        }
        # Submitting an incomplete form triggers errors
        response = self.client.post(account_signup_url, account_signup_form_content)
        self.assertFormError(response, 'form', 'email', 'This field is required.')
        self.assertFormError(response, 'form', 'password1', 'This field is required.')

    def test_signup_view_valid_form(self):
        account_signup_url = reverse('account_signup')
        user_name = 'Albus Dumbledore'
        user_email = 'albus@hogwarts.org'
        account_signup_form_content = {
            'name': user_name,
            'email': user_email,
            'password1': 'lemondrop',
        }
        response = self.client.post(account_signup_url, account_signup_form_content)
        self.assertEqual(302, response.status_code)
        # TODO (fsiddi) investigate why this redirects to profile details
        # instead of profile setup
        # self.assertEqual(reverse('profile_setup'), response.url)

        user = User.objects.get(email='albus@hogwarts.org')
        # Ensure that username is created after the name
        self.assertEqual('albusdumbledore', user.username)
        # Ensure that user name is saved
        self.assertEqual(user_name, user.profile.name)


class FollowToggleTest(TestViewsMixin):
    def test_follow_toggle(self):
        post = PostFactory(user=self.user1)

        community_attrs = {
            'content_type_id': ContentType.objects.get_for_model(Post).id,
            'object_id': post.id,
        }
        url_follow_toggle = reverse('follow-toggle', kwargs=community_attrs)

        # Try to follow as unauthenticated
        response = self.client.get(url_follow_toggle)
        self.assertEqual(response.status_code, 302)

        # Try again as authenticated
        self.client.force_login(self.user2)
        response = self.client.get(url_follow_toggle)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'ok', 'action': 'Started Following'})

        # Now unfollow
        response = self.client.get(url_follow_toggle)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'ok', 'action': 'Unfollowed'})
