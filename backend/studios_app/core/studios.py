from rest_framework import status

from backend.studios_app.models import Studio
from backend.studios_app.shared_utils.serializers import serialize_studio


class StudiosHandle:
    def __init__(self, request):
        self.request = request

    def all(self):
        studios = Studio.objects.all()
        data = [serialize_studio(studio, self.request) for studio in studios]
        return status.HTTP_200_OK, 'Studios fetched successfully.', {'studios': data}

    def view(self, pk):
        studio = Studio.objects.filter(pk=pk).first()
        if not studio:
            return status.HTTP_404_NOT_FOUND, 'Studio not found.', None
        return status.HTTP_200_OK, 'Studio fetched successfully.', {'studio': serialize_studio(studio, self.request)}

    def create(self):
        name = self.request.data.get('name')
        entity_type = self.request.data.get('entity_type')
        if not name or entity_type not in Studio.EntityType.values:
            return status.HTTP_400_BAD_REQUEST, 'name and a valid entity_type are required.', None

        studio = Studio.objects.create(name=name, entity_type=entity_type)
        return status.HTTP_201_CREATED, 'Studio created successfully.', {'studio': serialize_studio(studio, self.request)}

    def update(self, pk):
        studio = Studio.objects.filter(pk=pk).first()
        if not studio:
            return status.HTTP_404_NOT_FOUND, 'Studio not found.', None

        for field in ('name', 'entity_type'):
            if field in self.request.data:
                setattr(studio, field, self.request.data[field])
        studio.save()

        return status.HTTP_200_OK, 'Studio updated successfully.', {'studio': serialize_studio(studio, self.request)}

    def delete(self, pk):
        studio = Studio.objects.filter(pk=pk).first()
        if not studio:
            return status.HTTP_404_NOT_FOUND, 'Studio not found.', None
        studio.delete()
        return status.HTTP_200_OK, 'Studio deleted successfully.', None
