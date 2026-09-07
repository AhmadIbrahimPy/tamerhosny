from django.db import migrations


def delete_legacy_shared_challenges(apps, schema_editor):
    # These rows were "one global song for everyone" under the old
    # design - there's no user to attribute them to, and each user
    # simply gets a fresh row lazily created on their next visit under
    # the new per-user design, so dropping them loses nothing worth
    # keeping.
    #
    # Split into its own migration (schema changes follow in the next
    # one): deleting these rows fires deferred FK-check triggers from
    # DailyGuessAttempt's CASCADE, and Postgres refuses an ALTER TABLE
    # on the same table while those are still pending in the same
    # transaction ("cannot ALTER TABLE ... because it has pending
    # trigger events") - a real failure hit deploying this as one
    # migration.
    DailyGuessChallenge = apps.get_model('music_app', 'DailyGuessChallenge')
    DailyGuessChallenge.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('music_app', '0024_dailyguessattempt'),
    ]

    operations = [
        migrations.RunPython(delete_legacy_shared_challenges, migrations.RunPython.noop),
    ]
