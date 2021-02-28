import factory
from django.utils.text import slugify
from dillo.tests.factories.users import UserFactory
from dillo.models.communities import Community, CommunityCategory


class CommunityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Community
        django_get_or_create = ('name',)

    # user = factory.SubFactory(UserFactory)
    name = 'Today'
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    tagline = factory.Faker('sentence')
    description = factory.Faker('paragraph')
    visibility = 'public'
    is_featured = True


class CommunityCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CommunityCategory

    community = factory.SubFactory(CommunityFactory)
    name = 'News'
    slug = factory.LazyAttribute(lambda o: slugify(o))
