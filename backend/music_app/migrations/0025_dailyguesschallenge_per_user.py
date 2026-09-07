import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def delete_legacy_shared_challenges(apps, schema_editor):
    # These rows were "one global song for everyone" under the old
    # design - there's no user to attribute them to, and each user
    # simply gets a fresh row lazily created on their next visit under
    # the new per-user design, so dropping them loses nothing worth
    # keeping.
    DailyGuessChallenge = apps.get_model('music_app', 'DailyGuessChallenge')
    DailyGuessChallenge.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('music_app', '0024_dailyguessattempt'),
    ]

    operations = [
        migrations.RunPython(delete_legacy_shared_challenges, migrations.RunPython.noop),
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
