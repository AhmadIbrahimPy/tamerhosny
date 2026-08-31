# Generated migration for adding profile_image field to UserAccount model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraccount',
            name='profile_image',
            field=models.ImageField(blank=True, null=True, upload_to='users/profile_images/', verbose_name='صورة الملف الشخصي'),
        ),
    ]
