from datetime import datetime

from django.core.management.base import BaseCommand

from backend.media_app.models import Media


class Command(BaseCommand):
    help = 'Import Tamer Hosny movies'

    def handle(self, *args, **kwargs):
        movies_data = [
            {
                'title_ar': 'حالة حب',
                'title_en': 'Halet Hob',
                'release_date': datetime(2003, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'سيد العاطفي',
                'title_en': 'Sayed El Atefy',
                'release_date': datetime(2005, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'عمر وسلمى',
                'title_en': 'Omar & Salma',
                'release_date': datetime(2007, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'كابتن هيما',
                'title_en': 'Captain Hima',
                'release_date': datetime(2008, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'عمر وسلمى 2',
                'title_en': 'Omar & Salma 2',
                'release_date': datetime(2009, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'نور عيني',
                'title_en': 'Nour Einy',
                'release_date': datetime(2010, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'عمر وسلمى 3',
                'title_en': 'Omar & Salma 3',
                'release_date': datetime(2012, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'أهواك',
                'title_en': 'I Love You',
                'release_date': datetime(2015, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'تصبح على خير',
                'title_en': 'Tesbah Ala Kheir',
                'release_date': datetime(2017, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'البدلة',
                'title_en': 'El Badla',
                'release_date': datetime(2018, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'الفلوس',
                'title_en': 'Al Folous',
                'release_date': datetime(2019, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'مش أنا',
                'title_en': 'Mosh Ana',
                'release_date': datetime(2021, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'بحبك',
                'title_en': 'Bahebak',
                'release_date': datetime(2022, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'تاج',
                'title_en': 'Taj',
                'release_date': datetime(2023, 1, 1).date(),
                'media_type': 'MOVIE',
            },
            {
                'title_ar': 'ريستارت',
                'title_en': 'Restart',
                'release_date': datetime(2025, 1, 1).date(),
                'media_type': 'MOVIE',
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for movie_data in movies_data:
            title_ar = movie_data['title_ar']
            existing_movie = Media.objects.filter(title_ar=title_ar, media_type='MOVIE').first()
            
            if existing_movie:
                existing_movie.release_date = movie_data['release_date']
                existing_movie.save()
                updated_count += 1
                self.stdout.write(f'Updated: {title_ar}')
            else:
                Media.objects.create(
                    title_ar=title_ar,
                    title_en=movie_data['title_en'],
                    release_date=movie_data['release_date'],
                    media_type=movie_data['media_type'],
                    visibility='PUBLISHED'
                )
                created_count += 1
                self.stdout.write(f'Created: {title_ar}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully imported {created_count} movies, updated {updated_count} movies'
            )
        )
