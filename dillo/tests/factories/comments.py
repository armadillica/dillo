import factory
from django.contrib.contenttypes.models import ContentType

from dillo.models.posts import Comment
from dillo.tests.factories.users import UserFactory
from dillo.tests.factories.posts import PostFactory


class CommentedItemFactory(factory.django.DjangoModelFactory):
    entity_object_id = factory.SelfAttribute('entity.id')
    entity_content_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(o.entity)
    )

    class Meta:
        exclude = ['entity']
        abstract = True


class CommentForPostFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    content = factory.Faker('paragraph')
    entity = factory.SubFactory(PostFactory)
    parent_comment = None

    class Meta:
        model = Comment
