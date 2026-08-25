from django.utils.dateparse import parse_datetime


def parse_datetime_field(value):
    """Raw request data assigns strings straight onto model fields; a
    DateTimeField needs an actual datetime before any is_live/is_upcoming
    property comparison runs on the same request.
    """
    if not value or not isinstance(value, str):
        return value
    return parse_datetime(value)
