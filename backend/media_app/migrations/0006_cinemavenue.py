import django.db.models.deletion
from django.db import migrations, models


def migrate_screenings_to_venues(apps, schema_editor):
    CinemaScreening = apps.get_model('media_app', 'CinemaScreening')
    CinemaVenue = apps.get_model('media_app', 'CinemaVenue')
    for screening in CinemaScreening.objects.all():
        venue, _created = CinemaVenue.objects.get_or_create(
            name=screening.cinema_name, defaults={'city': screening.city},
        )
        screening.venue = venue
        screening.save(update_fields=['venue'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('media_app', '0005_cinemascreening'),
    ]

    operations = [
        migrations.CreateModel(
            name='CinemaVenue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('city', models.CharField(blank=True, max_length=120)),
            ],
            options={
                'ordering': ('city', 'name'),
            },
        ),
        migrations.AddField(
            model_name='cinemascreening',
            name='venue',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE, related_name='screenings',
                to='media_app.cinemavenue',
            ),
        ),
        migrations.RunPython(migrate_screenings_to_venues, noop_reverse),
        migrations.RemoveField(model_name='cinemascreening', name='cinema_name'),
        migrations.RemoveField(model_name='cinemascreening', name='city'),
        migrations.AlterField(
            model_name='cinemascreening',
            name='venue',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name='screenings',
                to='media_app.cinemavenue',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='cinemascreening',
            unique_together={('media', 'venue')},
        ),
        migrations.AlterModelOptions(
            name='cinemascreening',
            options={'ordering': ('venue__city', 'venue__name')},
        ),
    ]
