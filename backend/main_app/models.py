from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserAccount(AbstractUser):
    class Role(models.IntegerChoices):
        ADMIN = 1, _('Admin')
        EDITOR = 2, _('Editor')
        VIEWER = 3, _('Viewer')

    role = models.PositiveSmallIntegerField(choices=Role.choices, default=Role.EDITOR)

    # Roles allowed to log into the internal dashboard.
    DASHBOARD_ROLES = (Role.ADMIN, Role.EDITOR)

    def __str__(self):
        return self.username
