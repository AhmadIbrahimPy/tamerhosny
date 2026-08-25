from django import forms


class CircularAvatarWidget(forms.ClearableFileInput):
    """Renders an image field as a circular avatar: an "add" button when
    empty, or the current image (click to open full-size, with a delete
    button) when one is set.
    """

    template_name = 'dashboard/widgets/circular_avatar.html'


class SquareCoverWidget(forms.ClearableFileInput):
    """Same behaviour as CircularAvatarWidget but rendered as a rounded
    square — used for cover art rather than a person/logo avatar.
    """

    template_name = 'dashboard/widgets/square_cover.html'
