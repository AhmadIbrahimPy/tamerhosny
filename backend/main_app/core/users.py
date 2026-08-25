from rest_framework import status

from backend.main_app.models import UserAccount


class UsersHandle:
    def __init__(self, request):
        self.request = request

    def all(self):
        users = UserAccount.objects.all().order_by('username')
        data = [self._serialize(user) for user in users]
        return status.HTTP_200_OK, 'Users fetched successfully.', {'users': data}

    def view(self, pk):
        user = UserAccount.objects.filter(pk=pk).first()
        if not user:
            return status.HTTP_404_NOT_FOUND, 'User not found.', None
        return status.HTTP_200_OK, 'User fetched successfully.', {'user': self._serialize(user)}

    def create(self):
        username = self.request.data.get('username')
        password = self.request.data.get('password')
        role = self.request.data.get('role', UserAccount.Role.EDITOR)
        if not username or not password:
            return status.HTTP_400_BAD_REQUEST, 'username and password are required.', None
        if UserAccount.objects.filter(username=username).exists():
            return status.HTTP_400_BAD_REQUEST, 'username already exists.', None

        user = UserAccount.objects.create_user(username=username, password=password, role=role)
        return status.HTTP_201_CREATED, 'User created successfully.', {'user': self._serialize(user)}

    def update(self, pk):
        user = UserAccount.objects.filter(pk=pk).first()
        if not user:
            return status.HTTP_404_NOT_FOUND, 'User not found.', None

        for field in ('role', 'is_active'):
            if field in self.request.data:
                setattr(user, field, self.request.data[field])
        password = self.request.data.get('password')
        if password:
            user.set_password(password)
        user.save()
        return status.HTTP_200_OK, 'User updated successfully.', {'user': self._serialize(user)}

    def delete(self, pk):
        user = UserAccount.objects.filter(pk=pk).first()
        if not user:
            return status.HTTP_404_NOT_FOUND, 'User not found.', None
        user.delete()
        return status.HTTP_200_OK, 'User deleted successfully.', None

    @staticmethod
    def _serialize(user):
        return {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'is_active': user.is_active,
        }
