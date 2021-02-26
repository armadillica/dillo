from django.contrib.auth import get_user_model
import factory

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    username = factory.LazyAttribute(lambda o: f'{o.first_name}_{o.last_name}')
    email = factory.Faker('email')
    password = factory.Faker('password')
