import factory

from dillo.models.posts import Post
from dillo.tests.factories.users import UserFactory


class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post
        django_get_or_create = ('title',)

    user = factory.SubFactory(UserFactory)
    title = factory.Faker('sentence')
    content = factory.Faker('paragraph')
    visibility = 'public'
