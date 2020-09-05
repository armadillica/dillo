from django.apps import AppConfig


class DilloConfig(AppConfig):
    name = 'dillo'

    def ready(self):
        import dillo.signals  # noqa
        from actstream import registry
        from taggit.models import Tag
        from django.contrib.auth.models import User

        registry.register(self.get_model('Post'))
        registry.register(self.get_model('Comment'))
        registry.register(Tag)
        registry.register(User)
