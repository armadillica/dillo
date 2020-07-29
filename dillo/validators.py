from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy
import micawber

providers = micawber.bootstrap_basic()


def validate_reel_url(value):
    """Check if value is oembeddable and from a valid provider."""
    valid_providers = {
        'YouTube',
        'Vimeo',
    }

    # Try to extract oembed info from the url
    _, extracted_urls = providers.extract(value)

    # If no info is found at all, raise an error
    if value not in extracted_urls:
        raise ValidationError(
            gettext_lazy('%(value)s is not a supported url'), params={'value': value},
        )

    # Look for a valid provider
    provider_name = extracted_urls[value]['provider_name']
    if provider_name in valid_providers:
        return

    raise ValidationError(
        gettext_lazy('%(value)s is not a supported provider'), params={'value': provider_name},
    )
