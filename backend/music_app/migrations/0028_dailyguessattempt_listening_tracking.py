from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music_app', '0027_dailyguessattempt_hype_line_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailyguessattempt',
            name='play_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='dailyguessattempt',
            name='seconds_listened',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='dailyguessattempt',
            name='points_awarded',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
