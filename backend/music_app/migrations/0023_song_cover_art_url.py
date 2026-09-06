import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music_app', '0022_dailyguesschallenge'),
    ]

    operations = [
        migrations.AddField(
            model_name='song',
            name='cover_art_url',
            field=models.URLField(blank=True, validators=[django.core.validators.URLValidator(schemes=['http', 'https'])]),
        ),
    ]
