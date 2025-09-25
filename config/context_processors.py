from django.conf import settings


def global_settings(_request):
    """Expose selected Django settings to templates."""

    return {
        "DEBUG": settings.DEBUG,
    }
