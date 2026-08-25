from rest_framework import status

from backend.people_app.models import Person
from backend.people_app.shared_utils.serializers import serialize_person


class PeopleHandle:
    def __init__(self, request):
        self.request = request

    def all(self):
        people = Person.objects.all()
        data = [serialize_person(person, self.request) for person in people]
        return status.HTTP_200_OK, 'People fetched successfully.', {'people': data}

    def view(self, pk):
        person = Person.objects.filter(pk=pk).first()
        if not person:
            return status.HTTP_404_NOT_FOUND, 'Person not found.', None
        return status.HTTP_200_OK, 'Person fetched successfully.', {'person': serialize_person(person, self.request)}

    def create(self):
        name = self.request.data.get('name')
        if not name:
            return status.HTTP_400_BAD_REQUEST, 'name is required.', None

        person = Person.objects.create(
            name=name,
            bio=self.request.data.get('bio', ''),
        )
        return status.HTTP_201_CREATED, 'Person created successfully.', {'person': serialize_person(person, self.request)}

    def update(self, pk):
        person = Person.objects.filter(pk=pk).first()
        if not person:
            return status.HTTP_404_NOT_FOUND, 'Person not found.', None

        for field in ('name', 'bio'):
            if field in self.request.data:
                setattr(person, field, self.request.data[field])
        person.save()
        return status.HTTP_200_OK, 'Person updated successfully.', {'person': serialize_person(person, self.request)}

    def delete(self, pk):
        person = Person.objects.filter(pk=pk).first()
        if not person:
            return status.HTTP_404_NOT_FOUND, 'Person not found.', None
        person.delete()
        return status.HTTP_200_OK, 'Person deleted successfully.', None
