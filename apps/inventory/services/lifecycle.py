"""Computed lifecycle warnings and replacement planning helpers."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone


LIFECYCLE_DATES = (
    ('warranty_end_date', 'Warranty expiration', 'Warranty'),
    ('security_support_end_date', 'Security-support expiration', 'Security support'),
    ('end_of_life_date', 'End of life', 'End of life'),
)


def lifecycle_warnings(asset, *, as_of=None):
    """Return current lifecycle date states without persisting warning flags."""
    as_of = as_of or timezone.localdate()
    warning_limit = as_of + timedelta(days=settings.LIFECYCLE_WARNING_DAYS)
    warnings = []
    for field_name, label, key in LIFECYCLE_DATES:
        value = getattr(asset, field_name)
        if value is None:
            state = 'unknown'
        elif value < as_of:
            state = 'expired'
        elif value <= warning_limit:
            state = 'approaching'
        else:
            state = 'current'
        warnings.append({'field': field_name, 'label': label, 'key': key, 'date': value, 'state': state})
    missing = [name for name in ('installation_date', 'warranty_end_date', 'security_support_end_date', 'end_of_life_date', 'last_tested') if getattr(asset, name) is None]
    return {'warnings': warnings, 'missing_fields': missing, 'needs_review': bool(missing or any(item['state'] in ('expired', 'approaching') for item in warnings))}


def replacement_review_needed(asset):
    """Whether the current recommendation merits budget/replacement review."""
    return asset.replacement_recommendation in {'budget', 'priority', 'retire', 'verify'}
