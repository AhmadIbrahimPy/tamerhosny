from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_remix_app', '0002_remixproject_source_song_1_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='remixproject',
            name='error_message',
            field=models.TextField(blank=True, default='', verbose_name='Error Message'),
        ),
    ]
