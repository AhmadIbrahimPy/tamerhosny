from django.contrib import admin

from backend.people_app.models import Person


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('full_name_ar', 'primary_role', 'updated_at')
    list_filter = ('primary_role',)
    search_fields = ('full_name_ar', 'full_name_en')
    prepopulated_fields = {'slug': ('full_name_ar',)}
