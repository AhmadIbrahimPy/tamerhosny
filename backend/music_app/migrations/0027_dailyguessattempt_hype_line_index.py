from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music_app', '0026_dailyguesschallenge_user_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailyguessattempt',
            name='hype_line_index',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
