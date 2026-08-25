from django.contrib import admin

from backend.people_app.models import Person


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'updated_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
