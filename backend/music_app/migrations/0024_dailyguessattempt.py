import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('music_app', '0023_song_cover_art_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyGuessAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('correct', models.BooleanField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('challenge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attempts', to='music_app.dailyguesschallenge')),
                ('guessed_song', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='music_app.song')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_guess_attempts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddConstraint(
            model_name='dailyguessattempt',
            constraint=models.UniqueConstraint(fields=('user', 'challenge'), name='unique_daily_guess_attempt_per_user'),
        ),
    ]
