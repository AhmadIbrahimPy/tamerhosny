import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music_app', '0021_singwithtamerproject_processing_error_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyGuessChallenge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('song', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='music_app.song')),
            ],
            options={
                'ordering': ('-date',),
            },
        ),
    ]
