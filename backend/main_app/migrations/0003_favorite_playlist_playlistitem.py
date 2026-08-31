# Generated migration for adding Favorite, Playlist, and PlaylistItem models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0002_useraccount_profile_image'),
        ('music_app', '0010_song_audio_analysis_data_song_audio_bpm_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_type', models.CharField(choices=[('SONG', 'أغنية'), ('ALBUM', 'ألبوم'), ('PERSON', 'فنان'), ('MEDIA', 'وسائط')], max_length=20, verbose_name='نوع المحتوى')),
                ('object_id', models.PositiveIntegerField(verbose_name='معرف المحتوى')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to='main_app.useraccount', verbose_name='المستخدم')),
            ],
            options={
                'verbose_name': 'مفضل',
                'verbose_name_plural': 'المفضل',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Playlist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='اسم القائمة')),
                ('description', models.TextField(blank=True, verbose_name='الوصف')),
                ('is_public', models.BooleanField(default=False, verbose_name='عامة')),
                ('cover_image', models.ImageField(blank=True, null=True, upload_to='playlists/covers/', verbose_name='صورة الغلاف')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='playlists', to='main_app.useraccount', verbose_name='المستخدم')),
            ],
            options={
                'verbose_name': 'قائمة تشغيل',
                'verbose_name_plural': 'قوائم التشغيل',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PlaylistItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='الترتيب')),
                ('added_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')),
                ('playlist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='main_app.playlist', verbose_name='قائمة التشغيل')),
                ('song', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='playlist_items', to='music_app.song', verbose_name='الأغنية')),
            ],
            options={
                'verbose_name': 'عنصر قائمة التشغيل',
                'verbose_name_plural': 'عناصر قوائم التشغيل',
                'ordering': ['order', 'added_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='favorite',
            unique_together={('user', 'content_type', 'object_id')},
        ),
        migrations.AlterUniqueTogether(
            name='playlistitem',
            unique_together={('playlist', 'song')},
        ),
    ]
