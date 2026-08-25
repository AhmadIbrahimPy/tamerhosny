from django.contrib.auth.models import AbstractUser
from django.db import models


class UserAccount(AbstractUser):
    class Role(models.IntegerChoices):
        ADMIN = 1, 'Admin'
        EDITOR = 2, 'Editor'
        VIEWER = 3, 'Viewer'

    role = models.PositiveSmallIntegerField(choices=Role.choices, default=Role.EDITOR)

    # Roles allowed to log into the internal dashboard.
    DASHBOARD_ROLES = (Role.ADMIN, Role.EDITOR)

    def __str__(self):
        return self.username
