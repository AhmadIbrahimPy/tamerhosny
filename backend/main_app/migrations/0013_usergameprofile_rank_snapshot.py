from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0012_usergameprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='usergameprofile',
            name='previous_rank',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='usergameprofile',
            name='rank_snapshot_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
