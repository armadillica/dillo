import datetime
import pathlib
import tempfile
from actstream import models as models_actstream
from actstream.actions import unfollow, follow
from django.core import mail
from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User

import dillo.models.events
import dillo.models.mixins
import dillo.models.posts
import dillo.models.profiles


class ProfileModelTest(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(username='testuser', password='12345')

    def test_profile_created_after_user(self):
        from dillo.models.profiles import Profile

        """Ensure that profile is attached to a newly created user."""
        self.assertIsInstance(self.user.profile, Profile)

    def test_social_links_parsing(self):
        from dillo.models.profiles import ProfileLinks

        p = ProfileLinks.objects.create(
            profile=self.user.profile, url='https://www.instagram.com/tunameltsmyheart/', social=''
        )
        self.assertEqual('instagram', p.social)

    def test_get_absolute_url(self):
        expected_url = '/testuser/'
        self.assertEqual(expected_url, self.user.profile.get_absolute_url())

    def test_next_events_attending(self):
        # Create an event in the far future, so we don't have to mock the now()
        # for the next 100 years.
        event1 = dillo.models.events.Event.objects.create(
            name='Event1',
            slug='event1',
            website='http://example.com',
            starts_at=datetime.datetime(2120, 2, 11, 10, tzinfo=datetime.timezone.utc),
            ends_at=datetime.datetime(2120, 2, 11, 22, tzinfo=datetime.timezone.utc),
        )
        self.assertNotIn(event1, self.user.events.all())
        # Assign event to user
        event1.attendees.add(self.user)
        # Ensure the event is in the upcoming events
        self.assertIn(event1, self.user.profile.next_events_attending)

        # Create new event
        event2 = dillo.models.events.Event.objects.create(
            name='Event2',
            slug='event2',
            website='http://example.com',
            starts_at=datetime.datetime(2019, 2, 11, 10, tzinfo=datetime.timezone.utc),
            ends_at=datetime.datetime(2019, 2, 11, 22, tzinfo=datetime.timezone.utc),
        )
        # Assign event to user
        event2.attendees.add(self.user)
        # Ensure that the event was assigned
        self.assertIn(event2, self.user.events.all())
        # Ensure the event does not show up in next events (it's past)
        self.assertNotIn(event2, self.user.profile.next_events_attending)

    def test_likes_decrease(self):
        from dillo.signals import profile_likes_count_decrease

        dillo.models.profiles.Profile.objects.filter(user=self.user).update(likes_count=1)
        profile_likes_count_decrease(self.user)
        self.assertEqual(self.user.profile.likes_count, 0)
        # Here an exception is raised, handled and the likes count is reset to 0
        profile_likes_count_decrease(self.user)
        self.assertEqual(self.user.profile.likes_count, 0)

    @override_settings(MEDIA_ROOT=tempfile.TemporaryDirectory(prefix='animato_test').name)
    def test_process_reel_url(self):
        """Try fetching oembed data if profile.reel exists."""
        self.assertEqual('', self.user.profile.reel)
        self.user.profile.reel = "https://vimeo.com/325910798"
        self.user.profile.save()
        self.assertIsNotNone(self.user.profile.reel)

    def test_first_name_guess(self):
        self.assertIsNone(self.user.profile.first_name_guess)
        # Set name attribute.
        self.user.profile.name = 'James'
        self.assertEqual('James', self.user.profile.first_name_guess)
        # Set name attribute to have first and last name-
        self.user.profile.name = 'Harry Potter'
        self.assertEqual('Harry', self.user.profile.first_name_guess)


class PostModelTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        from dillo.models.posts import Post

        self.user = User.objects.create_user(username='testuser', password='12345')
        self.post = Post.objects.create(user=self.user, title='Velocità con #animato')

    def test_post_creation(self):
        from dillo.models.posts import Post

        # Create Post with a hasthag
        saved_post = Post.objects.get(id=self.post.id)
        # Ensure the tag has been assigned to the Post
        self.assertIn('animato', saved_post.tags.names())

    def test_post_publish_set_published_at(self):
        from dillo.models.posts import Post

        # Create Post with a hasthag
        saved_post = Post.objects.get(id=self.post.id)
        self.assertEqual('draft', saved_post.status)
        self.assertIsNone(saved_post.published_at)
        saved_post.publish()
        self.assertEqual('published', saved_post.status)
        self.assertIsNotNone(saved_post.published_at)

    def test_multiple_tags(self):
        from dillo.models.posts import Post

        # Create Post with two hasthags
        post = Post.objects.create(user=self.user, title='Velocità #con #animato')
        saved_post = Post.objects.get(id=post.id)
        # Ensure the tags have been assigned to the Post
        self.assertIn('animato', saved_post.tags.names())
        self.assertIn('con', saved_post.tags.names())

    def test_post_no_tags(self):
        from dillo.models.posts import Post

        # Create Post without a title
        post = Post.objects.create(user=self.user)
        saved_post = Post.objects.get(id=post.id)
        self.assertEqual(saved_post.user, self.user)
        self.assertIsNone(saved_post.title)

    def test_post_delete(self):
        from dillo.models.posts import Comment
        from dillo.models.posts import Post

        # Add Comment to Post
        comment = Comment.objects.create(
            user=self.user, post=self.post, content='My comment #Гарри'
        )
        # TODO(fsiddi) Add image
        self.post.delete()
        # Ensure that Post and Comment are deleted
        with self.assertRaises(Comment.DoesNotExist):
            Comment.objects.get(pk=comment.id)
        with self.assertRaises(Post.DoesNotExist):
            Post.objects.get(pk=self.post.id)

    def test_post_like(self):
        from dillo.models.mixins import Likes

        # Test creating like
        self.post.like_toggle(self.user)
        post_like = Likes.objects.get(
            user=self.user, content_type_id=self.post.content_type_id, object_id=self.post.id
        )
        self.assertEqual(post_like.user, self.user)

        # Test removing like
        self.post.like_toggle(self.user)
        with self.assertRaises(Likes.DoesNotExist):
            Likes.objects.get(
                user=self.user, content_type_id=self.post.content_type_id, object_id=self.post.id
            )

    def test_post_like_count(self):
        from django.contrib.auth.models import User

        other_user = User.objects.create_user(username='otheruser', password='12345')
        self.post.like_toggle(self.user)
        self.post.like_toggle(other_user)
        self.assertEqual(2, self.post.likes.count())

    def test_post_like_labels(self):
        """Test the output of like_toggle.

        The tuple output is used in the UI.
        """
        from django.contrib.auth.models import User

        action, action_label, likes_count, likes_word = self.post.like_toggle(self.user)
        self.assertEqual('liked', action)
        self.assertEqual('Liked', action_label)
        self.assertEqual('1 LIKE', f'{likes_count} {likes_word}')
        other_user = User.objects.create_user(username='otheruser', password='12345')
        _, _, likes_count, likes_word = self.post.like_toggle(other_user)
        self.assertEqual('2 LIKES', f'{likes_count} {likes_word}')
        self.post.like_toggle(other_user)
        _, _, likes_count, likes_word = self.post.like_toggle(self.user)
        self.assertEqual('0 LIKES', f'{likes_count} {likes_word}')

    def test_post_absolute_url(self):
        absolute_url = reverse('post_detail', kwargs={'hash_id': self.post.hash_id})
        self.assertEqual(f'http://example.com{absolute_url}', self.post.absolute_url)

    def test_post_edit_tags(self):
        self.post.title = "Here we have go with #b3d"
        self.post.save()
        self.assertIn('b3d', self.post.tags.names())

    def test_post_edit_mentions(self):
        self.post.title = "Here @testuser goes with animato"
        self.post.save()
        self.assertIn(self.user, self.post.mentioned_users)
        self.post.title = "Here testuser is gone"
        self.post.save()
        self.assertEqual([], self.post.mentioned_users)

    def test_trending_tags(self):
        dillo.models.posts.Post.objects.create(user=self.user, title='Post with #b3d')
        # Ensure that there are 2 trending tags
        self.assertEqual(len(dillo.models.posts.get_trending_tags()), 2)
        dillo.models.posts.Post.objects.create(user=self.user, title='Post with #b3d')
        # Ensure that #b3d is at the first place
        self.assertEqual(dillo.models.posts.get_trending_tags()[0].slug, 'b3d')
        # Now add 2 more posts with #animato
        dillo.models.posts.Post.objects.create(user=self.user, title='Post with #animato')
        dillo.models.posts.Post.objects.create(user=self.user, title='Post with #animato')
        # Ensure that #animato is at first place
        self.assertEqual(dillo.models.posts.get_trending_tags()[0].slug, 'animato')


class CommentModelTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        from dillo.models.posts import Post

        self.user = User.objects.create_user(username='testuser', password='12345')
        self.post = Post.objects.create(user=self.user, title='My post')

    def test_comment_creation(self):
        from dillo.models.posts import Comment

        comment = Comment.objects.create(
            user=self.user, post=self.post, content='My comment #b3d #Гарри'
        )
        # Fetch saved comment
        saved_comment = Comment.objects.get(id=comment.id)
        # Ensure the content of the comment is correct
        self.assertEquals(saved_comment.content, 'My comment #b3d #Гарри')
        # Ensure that the tag has been assigned to the Comment
        self.assertIn('Гарри', saved_comment.tags.names())

    def test_comment_reply_creation(self):
        """Ensure that one level replies only are possible."""
        from dillo.models.posts import Comment
        from django.core.exceptions import FieldError

        comment = Comment.objects.create(user=self.user, post=self.post, content='My comment #b3d')
        reply = Comment.objects.create(
            user=self.user, post=self.post, parent_comment=comment, content='My reply'
        )

        # Ensure that replies to replies are not allowed
        with self.assertRaises(FieldError):
            Comment.objects.create(
                user=self.user, post=self.post, parent_comment=reply, content='My reply to reply'
            )

    def test_comment_deletion(self):
        """Test comment and tag association deletion."""
        from django.contrib.contenttypes.models import ContentType
        from taggit.models import TaggedItem
        from dillo.models.posts import Comment

        comment = Comment.objects.create(user=self.user, post=self.post, content='My comment #b3d')
        comment_id = comment.id
        comment_content_type = ContentType.objects.get(app_label='dillo', model='comment')
        comment.delete()

        with self.assertRaises(Comment.DoesNotExist):
            Comment.objects.get(pk=comment_id)

        with self.assertRaises(TaggedItem.DoesNotExist):
            TaggedItem.objects.get(object_id=comment_id, content_type=comment_content_type)

    def test_comments_count(self):
        from dillo.models.posts import Comment

        # Ensure the comment count for the post is correct
        self.assertEquals(self.post.comments_count, 0)
        Comment.objects.create(user=self.user, post=self.post, content='My comment #Гарри')
        # Ensure the comment count for the post is correct
        self.assertEquals(self.post.comments_count, 1)


class ActivitiesTest(TestCase):
    """Tests for the activity stream module."""

    def setUp(self):
        """Create two users and let one user create a post."""
        from django.contrib.auth.models import User
        from dillo.models.posts import Post

        self.user_ron = User.objects.create_user(username='ron', password='12345')
        self.user_harry = User.objects.create_user(username='harry', password='12345')
        self.post = Post.objects.create(user=self.user_ron, title='Sighted! #Гарри #hogwarts')
        self.post.publish()

    def test_object_activity(self):
        """Ensure that there is an activity stream for a certain post."""
        from actstream.models import action_object_stream

        # Verify there is activity for 'posting' and 'following' the post
        self.assertEqual(2, len(action_object_stream(self.post)))

    def test_follow_unfollow_tag(self):
        """Following a tag should show a post."""
        from actstream.actions import follow, unfollow
        from actstream.models import user_stream
        from taggit.models import Tag

        # Lookup the 'hogwarts' Tag
        hogwarts_tag = Tag.objects.get(name='hogwarts')
        # Follow it with the current user
        follow(self.user_harry, hogwarts_tag, actor_only=False)
        # Ensure that user_harry has one item in the stream
        self.assertEqual(1, len(user_stream(self.user_harry)))
        # Ensure that unfollowing the tag clears the user_stream
        unfollow(self.user_harry, hogwarts_tag)
        self.assertEqual(0, len(user_stream(self.user_harry)))


class TemplateFiltersTest(TestCase):
    def test_tags_parsing(self):
        from dillo.templatetags.dillo_filters import linkify_tags_and_mentions

        title_original = 'One #b3d for #àll.'
        title_parsed_expected = (
            'One <a href="/explore/tags/b3d">#b3d</a> for '
            '<a href="/explore/tags/%C3%A0ll">#àll</a>.'
        )
        title_parsed = linkify_tags_and_mentions(title_original)
        self.assertEqual(title_parsed, title_parsed_expected)

    def test_tags_nested_pound(self):
        from dillo.templatetags.dillo_filters import linkify_tags_and_mentions

        title_original = 'One #b3d#b4d.'
        title_parsed_expected = 'One <a href="/explore/tags/b3d">#b3d</a>#b4d.'
        title_parsed = linkify_tags_and_mentions(title_original)
        self.assertEqual(title_parsed, title_parsed_expected)

    def test_mentions_parsing(self):
        from django.contrib.auth.models import User
        from dillo.templatetags.dillo_filters import linkify_tags_and_mentions

        # Create user to be mentioned
        User.objects.create_user(username='venomgfx')
        title_original = 'One #b3d for @venomgfx.'
        title_parsed_expected = (
            'One <a href="/explore/tags/b3d">#b3d</a> for ' '<a href="/venomgfx/">@venomgfx</a>.'
        )
        title_parsed = linkify_tags_and_mentions(title_original)
        self.assertEqual(title_parsed, title_parsed_expected)

    def test_mentions_parsing_non_existing_user(self):
        from dillo.templatetags.dillo_filters import linkify_tags_and_mentions

        title_original = 'One #b3d for @venomgfx.'
        title_parsed_expected = 'One <a href="/explore/tags/b3d">#b3d</a> for ' '@venomgfx.'
        title_parsed = linkify_tags_and_mentions(title_original)
        self.assertEqual(title_parsed, title_parsed_expected)


class TagsExtractionTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(username='testuser')

    def test_tags_punctuation(self):
        from dillo.models.posts import Post

        post = Post.objects.create(user=self.user, title='Velocità con #animato!')
        self.assertEqual(post.tags.names()[0], 'animato')

        post = Post.objects.create(user=self.user, title='Velocità con #caminandes??')
        self.assertEqual(post.tags.names()[0], 'caminandes')

        post = Post.objects.create(user=self.user, title='Velocità con ##b3d??')
        self.assertEqual(post.tags.names()[0], 'b3d')

        post = Post.objects.create(user=self.user, title='Velocità con ##Гарри??')
        self.assertEqual(post.tags.names()[0], 'Гарри')


class MentionsExtractionTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(username='testuser')
        self.user_mentioned = User.objects.create_user(username='venomgfx')

    def test_mention_detection(self):
        from dillo.models.posts import Post

        post = Post.objects.create(user=self.user, title='Velocità con @venomgfx!')
        self.assertIn(self.user_mentioned, post.mentioned_users)

    def test_mention_non_existing_user(self):
        from dillo.models.posts import Post

        post = Post.objects.create(user=self.user, title='Velocità con @none!')
        self.assertFalse(post.mentioned_users)


class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.user_mentioned = User.objects.create_user(username='venomgfx')
        self.post = dillo.models.posts.Post.objects.create(
            user=self.user, title='Velocità con #animato',
        )

    def test_delete_user(self):
        self.user.delete()
        with self.assertRaises(dillo.models.posts.Post.DoesNotExist):
            dillo.models.posts.Post.objects.get(pk=self.post.id)


class FeedElementModelTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.user1 = User.objects.create_user(
            username='testuser1', email='testuser1@example.com', password='12345'
        )
        self.user2 = User.objects.create_user(
            username='testuser2', email='testuser2@example.com', password='12345'
        )
        self.post = dillo.models.posts.Post.objects.create(
            user=self.user1, title='Velocità con #animato'
        )

    def test_user_follows_own_post(self):
        self.assertIn(self.user1, models_actstream.followers(self.post))

    def test_user_liked_your_post_notification(self):
        """When user2 likes user1's post. User1 gets a notification."""
        # We publish the post created in setUp
        self.post.publish()
        self.post.like_toggle(self.user2)
        # Check that a like notification was generated for user1
        notification = self.user1.feed_entries.first()
        self.assertEqual('notification', notification.category)
        self.assertEqual('liked', notification.action.verb)
        # User2 does not have any notification
        self.assertEqual(0, self.user2.feed_entries.count())
        # Test that one email message has been sent
        # TODO(fsiddi) Improve email sending
        self.assertEqual(len(mail.outbox), 1)

    def test_user_commented_on_your_post_notification(self):
        # Create comment
        comment_content = 'Nice idea! #idea'
        comment = dillo.models.posts.Comment.objects.create(
            user=self.user2, content=comment_content, post=self.post,
        )
        notification = self.user1.feed_entries.first()
        self.assertEqual('notification', notification.category)
        self.assertEqual('commented', notification.action.verb)
        self.assertEqual(comment.id, notification.action.action_object.id)

        # Own comments do not generate notifications
        comment_content = 'My own comment'
        dillo.models.posts.Comment.objects.create(
            user=self.user1, content=comment_content, post=self.post,
        )
        notifications_count = self.user1.feed_entries.count()
        # We still have one notification, from the previous activity
        self.assertEqual(1, notifications_count)

        # If user does not follow post, do not generate notifications
        unfollow(self.user1, self.post)
        comment_content = 'A second comment!'
        dillo.models.posts.Comment.objects.create(
            user=self.user2, content=comment_content, post=self.post,
        )
        notifications_count = self.user1.feed_entries.count()
        # We still have one notification, from the previous activity
        self.assertEqual(1, notifications_count)

    def test_user_liked_your_comment_notification(self):
        # Create comment
        comment_content = 'Nice idea! #idea'
        comment = dillo.models.posts.Comment.objects.create(
            user=self.user1, content=comment_content, post=self.post,
        )
        comment.like_toggle(self.user2)
        notification = self.user1.feed_entries.first()
        # Verify that notification exists
        self.assertEqual('notification', notification.category)
        self.assertEqual('liked', notification.action.verb)
        self.assertEqual(comment_content, notification.action.action_object.content)

    def test_user_replied_to_your_comment_notification(self):
        # We publish the post created in setUp
        self.post.publish()
        # Create comment
        comment_content = 'Nice idea! #idea'
        comment = dillo.models.posts.Comment.objects.create(
            user=self.user1, content=comment_content, post=self.post,
        )
        reply_content = 'I concur.'
        # Add reply from the same user
        dillo.models.posts.Comment.objects.create(
            user=self.user1, content=reply_content, post=self.post, parent_comment=comment,
        )
        # This generates no notifications
        notifications_count = self.user1.feed_entries.filter(category='notification').count()
        self.assertEqual(0, notifications_count)

        # Add reply from another user
        reply = dillo.models.posts.Comment.objects.create(
            user=self.user2, content=reply_content, post=self.post, parent_comment=comment,
        )
        notification = self.user1.feed_entries.first()
        # Verify that notification exists
        self.assertEqual('notification', notification.category)
        self.assertEqual('replied', notification.action.verb)
        self.assertEqual(reply.content, notification.action.action_object.content)
        # Verify that one email notification was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Your comment has a new reply!')

    def test_user_mentioned_you_in_post(self):
        pass

    def test_user_mentioned_you_in_comment(self):
        pass

    def test_user_liked_a_post_where_you_are_mentioned(self):
        pass

    def test_user_liked_a_comment_where_you_are_mentioned(self):
        pass

    def test_user_follows_you_notification(self):
        # We publish the post created in setUp
        self.post.publish()
        follow(self.user2, self.user1)
        notification = self.user1.feed_entries.first()
        # Verify that notification exists
        self.assertEqual('notification', notification.category)
        self.assertEqual('started following', notification.action.verb)
        self.assertEqual(self.user2, notification.action.actor)
        # Verify that unfollow/follow does not create a new notifications
        unfollow(self.user2, self.user1)
        follow(self.user2, self.user1)
        self.assertEqual(2, self.user1.feed_entries.count())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'You have a new follower!')

    def test_post_in_timeline_for_user_followed(self):
        from taggit.models import Tag

        # We publish the post created in setUp
        self.post.publish()

        follow(self.user2, self.user1)
        follow(self.user2, Tag.objects.get(name='animato'))
        new_post = dillo.models.posts.Post.objects.create(
            user=self.user1, title='Follow me with #animato'
        )
        new_post.publish()

        # Verify that the post appears in the user timeline
        expected_timeline_post = (
            self.user2.feed_entries.filter(category='timeline').first().action.action_object
        )
        self.assertEqual(new_post, expected_timeline_post)

        # Verify that the there is only one entry in the timeline,
        # despite user2 follows both user1 and the animato tag
        self.assertEqual(2, self.user2.feed_entries.filter(category='timeline').count())

    def test_post_in_timeline_for_tag_followed(self):
        from taggit.models import Tag

        # We publish the post created in setUp
        self.post.publish()

        follow(self.user2, Tag.objects.get(name='animato'))
        follow(self.user2, Tag.objects.create(name='b3d'))
        new_post = dillo.models.posts.Post.objects.create(
            user=self.user1, title='Follow me with #animato #b3d'
        )
        new_post.publish()

        # Verify that the post appears in the user timeline
        expected_timeline_post = (
            self.user2.feed_entries.filter(category='timeline').first().action.action_object
        )
        self.assertEqual(new_post, expected_timeline_post)

        # Verify that the there is only one entry in the timeline,
        # despite user2 follows both the animato and the b3d tag
        self.assertEqual(2, self.user2.feed_entries.filter(category='timeline').count())

    def test_post_in_timeline_is_deleted(self):
        follow(self.user2, self.user1)
        new_post = dillo.models.posts.Post.objects.create(
            user=self.user1, title='Follow me with #animato'
        )
        new_post.publish()

        # Verify that the there is one entry in the timeline
        self.assertEqual(1, self.user2.feed_entries.filter(category='timeline').count())

        # Delete the post
        new_post.delete()

        # There will be no entry in the timeline
        self.assertEqual(0, self.user2.feed_entries.filter(category='timeline').count())

    def test_post_in_own_timeline(self):
        # User 1 timeline contains one post
        self.assertEqual(0, self.user1.feed_entries.filter(category='timeline').count())
        # We publish the post created in setUp
        self.post.publish()
        # The timeline features one entry
        self.assertEqual(1, self.user1.feed_entries.filter(category='timeline').count())


class UploadPathTest(SimpleTestCase):
    def test_get_upload_to_hashed_path_video(self):
        f = dillo.models.mixins.get_upload_to_hashed_path(
            dillo.models.posts.PostMediaVideo(), 'video.mp4'
        )
        file_path = pathlib.Path(f)
        file_name = file_path.name
        self.assertEqual(file_path.parts[0], file_name[:2])
        self.assertEqual(file_path.parts[1], file_name[2:4])
        self.assertEqual(file_path.parts[2], file_path.stem)

    def test_get_upload_to_hashed_path_image(self):
        f = dillo.models.mixins.get_upload_to_hashed_path(
            dillo.models.posts.PostMediaImage(), 'image.mp4'
        )
        file_path = pathlib.Path(f)
        file_name = file_path.name
        self.assertEqual(file_path.parts[0], file_name[:2])
        self.assertEqual(file_path.parts[1], file_name[2:4])
        self.assertEqual(file_path.parts[2], file_name)


class JobsModelTest(TestCase):
    def setUp(self):
        from dillo.models.posts import PostJob

        self.user = User.objects.create_user(username='testuser', password='12345')
        self.job = PostJob.objects.create(
            user=self.user,
            company='Minstry of Magic',
            city='London',
            country='UK',
            title='Minister of Magic',
            description='Plain regular description',
            url_apply='https://ministry.magic',
        )

    def test_created_job(self):
        self.assertEqual("Minister of Magic", self.job.title)

    def test_update_job_with_invalid_html(self):
        self.job.description = '<script>evil()</script>'
        self.job.save()
        # Ensure the <script> tag is escaped
        self.assertEqual('&lt;script&gt;evil()&lt;/script&gt;', self.job.description)

    def test_update_job_with_valid_html(self):
        self.job.description = '<strong>Good boi</strong>'
        self.job.save()
        self.assertEqual('<strong>Good boi</strong>', self.job.description)


class ModificationAwarenessMixinTest(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(username='testuser')

    def test_change_awareness_for_profile(self):
        self.user.profile.name = 'James'
        self.user.profile.save()
