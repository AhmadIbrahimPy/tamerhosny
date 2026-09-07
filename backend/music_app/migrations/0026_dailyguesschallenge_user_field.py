import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('music_app', '0025_dailyguesschallenge_per_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dailyguesschallenge',
            name='date',
            field=models.DateField(),
        ),
        migrations.AddField(
            model_name='dailyguesschallenge',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='daily_guess_challenges', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name='dailyguesschallenge',
            constraint=models.UniqueConstraint(fields=('date', 'user'), name='unique_daily_guess_challenge_per_user'),
        ),
    ]
