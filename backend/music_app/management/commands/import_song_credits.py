from django.core.management.base import BaseCommand

from backend.music_app.models import Song, SongCredit
from backend.people_app.models import Person


class Command(BaseCommand):
    help = 'Import credits for Tamer Hosny songs'

    def handle(self, *args, **kwargs):
        # Get Tamer Hosny
        tamer_hosny = Person.objects.filter(full_name_ar='تامر حسني').first()
        if not tamer_hosny:
            self.stdout.write(self.style.ERROR('Tamer Hosny not found in database'))
            return

        # Song credits data based on available information
        song_credits = {
            # Album: مش هتكرر (2026)
            'بنت مين': {
                'lyricists': [('أمير طعيمة', 'Amer Taaema')],
                'composers': [('عمرو مصطفى', 'Amr Mostafa')],
                'arrangers': [('عادل حقي', 'Adel Haki')],
            },
            'وش الخير': {
                'lyricists': [('تامر حسني', 'Tamer Hosny'), ('عبد المنعم طه', 'Abdel Monem Taher')],
                'composers': [('تامر حسني', 'Tamer Hosny'), ('كريم محسن', 'Karim Mohsen')],
                'arrangers': [('النابلسي', 'El Nabulsi')],
            },
            'يا خسارتنا': {
                'lyricists': [('تامر حسين', 'Tamer Hussein')],
                'composers': [('عمرو مصطفى', 'Amr Mostafa')],
                'arrangers': [('أحمد عادل', 'Ahmed Adel')],
            },
            'ما تيجي': {
                'lyricists': [('بلال سرور', 'Bilal Sarour')],
                'composers': [('بلال سرور', 'Bilal Sarour')],
                'arrangers': [('Kay Music', 'Kay Music')],
            },
            'مولعينها': {
                'lyricists': [('مصطفى حدوتة', 'Mostafa Hadouta')],
                'composers': [('إيهاب عبد الواحد', 'Ehab Abdel Wahed')],
                'arrangers': [('كوليبكس', 'Colibex')],
            },
            'عايزك توعديني': {
                'lyricists': [('أمير طعيمة', 'Amer Taaema')],
                'composers': [('عمرو مصطفى', 'Amr Mostafa')],
                'arrangers': [('عمرو مصطفى', 'Amr Mostafa'), ('تامر حسني', 'Tamer Hosny')],
            },
            'قال فاكرني': {
                'lyricists': [('مصطفى ناصر', 'Mostafa Naser')],
                'composers': [('محمد يحيى', 'Mohamed Yehia')],
                'arrangers': [('إلهامي دهيمة', 'Elhamy Dehima'), ('أحمد حسام', 'Ahmed Hossam')],
            },
            'مش هتكرر': {
                'lyricists': [('محمد يحيى', 'Mohamed Yehia')],
                'composers': [('محمد يحيى', 'Mohamed Yehia')],
                'arrangers': [('خالد نبيل', 'Khaled Nabil')],
            },
            'في القلب إنت': {
                'lyricists': [('تامر حسين', 'Tamer Hussein')],
                'composers': [('عزيز الشافعي', 'Aziz El Shafei')],
                'arrangers': [('حسام الصعبي', 'Hossam El Saabi')],
            },
            'ماتمشيش': {
                'lyricists': [('تامر حسني', 'Tamer Hosny')],
                'composers': [('تامر حسني', 'Tamer Hosny')],
                'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
            },
            'بعيش على الذكرى': {
                'lyricists': [('أمير طعيمة', 'Amer Taaema')],
                'composers': [('عمرو مصطفى', 'Amr Mostafa')],
                'arrangers': [('جلال فهمي', 'Galal Fahmy')],
            },
            'دهب قشرة': {
                'lyricists': [('ڤانتا', 'Vanta')],
                'composers': [('محمد يحيى', 'Mohamed Yehia')],
                'arrangers': [('يحيى يوسف', 'Yahya Youssef')],
            },
            'متأثر بغيابه': {
                'lyricists': [('تامر حسين', 'Tamer Hussein')],
                'composers': [('عزيز الشافعي', 'Aziz El Shafei')],
                'arrangers': [('جلال حمداوي', 'Galal Hamdawi')],
            },
            'اتحامى فيا': {
                'lyricists': [('تامر حسني', 'Tamer Hosny'), ('أحمد المالكي', 'Ahmed El Malki')],
                'composers': [('تامر حسني', 'Tamer Hosny'), ('محمد يحيى', 'Mohamed Yehia')],
                'arrangers': [('أحمد عبد السلام', 'Ahmed Abdel Salam')],
            },
            # Album: لينا معاد (2025)
            'الاحتياج وحش': {
                'lyricists': [('محمد القاياتي', 'Mohamed El Qayati')],
                'composers': [('بلال سرور', 'Bilal Sarour')],
                'arrangers': [('علي فتح الله', 'Ali Fathallah')],
            },
            'الأنوثة الطاغية': {
                'lyricists': [('تامر حسني', 'Tamer Hosny')],
                'composers': [('تامر حسني', 'Tamer Hosny')],
                'arrangers': [('وسام محمد', 'Wessam Mohamed')],
            },
            'لينا معاد': {
                'lyricists': [('تامر حسني', 'Tamer Hosny'), ('شريف مكاوي', 'Sherif Makawi')],
                'composers': [('شريف مكاوي', 'Sherif Makawi')],
                'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
            },
            'الذوق العالي': {
                'lyricists': [('تامر حسين', 'Tamer Hussein')],
                'composers': [('محمد رحيم', 'Mohamed Rahim')],
                'arrangers': [('أحمد طارق يحيى', 'Ahmed Tarek Yehia')],
            },
            'حبيبي تقلان': {
                'lyricists': [('تامر حسني', 'Tamer Hosny')],
                'composers': [('تامر حسني', 'Tamer Hosny')],
                'arrangers': [('علي فتح الله', 'Ali Fathallah')],
            },
            'يا حب': {
                'lyricists': [('ملاك عادل', 'Malak Adel')],
                'composers': [('محمد يحيى', 'Mohamed Yehia')],
                'arrangers': [('أحمد عبد السلام', 'Ahmed Abdel Salam')],
            },
            'مستني إيه': {
                'lyricists': [('عليم', 'Alim')],
                'composers': [('سام محمد', 'Samed Mohamed')],
                'arrangers': [('أحمد عبد السلام', 'Ahmed Abdel Salam')],
            },
            'واحشني يابن اللذينة': {
                'lyricists': [('تامر حسني', 'Tamer Hosny')],
                'composers': [('تامر حسني', 'Tamer Hosny')],
                'arrangers': [('النابلسي', 'El Nabulsi')],
            },
            'حبك لو غلطة': {
                'lyricists': [('تامر حسني', 'Tamer Hosny')],
                'composers': [('تامر حسني', 'Tamer Hosny')],
                'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
            },
            'يالا يا كداب': {
                'lyricists': [('تامر حسني', 'Tamer Hosny'), ('عمر عبده', 'Omar Abdu')],
                'composers': [('عمرو الشاذلي', 'Amro El Shazly')],
                'arrangers': [('محمد ياسر', 'Mohamed Yasser')],
            },
            'خلونا نشوفكم تاني': {
                'lyricists': [('محمود أنور', 'Mahmoud Anwar')],
                'composers': [('محمود أنور', 'Mahmoud Anwar')],
                'arrangers': [('محمد مجدي', 'Mohamed Magdi')],
            },
            # Album: عشأنجي (2022)
            'عشأنجي': {
                'lyricists': [('حمادة السيد', 'Hamada El Sayed')],
                'composers': [('مديح', 'Medih')],
                'arrangers': [('أمير محروس', 'Amir Mahrous')],
            },
            'مابجيش بالطريقة دي': {
                'lyricists': [('تامر حسين', 'Tamer Hussein')],
                'composers': [('تامر علي', 'Tamer Ali')],
                'arrangers': [('يحيى يوسف', 'Yahya Youssef')],
            },
            'سوحنا': {
                'lyricists': [('محمد عاطف', 'Mohamed Atef')],
                'composers': [('أحمد زعيم', 'Ahmed Zaeem')],
                'arrangers': [('وسام عبد المنعم', 'Wessam Abdel Monem')],
            },
            'خدنا مناعة': {
                'lyricists': [('أحمد المالكي', 'Ahmed El Malki')],
                'composers': [('بلال سرور', 'Bilal Sarour')],
                'arrangers': [('توما', 'Toma')],
            },
            'ليه طلة': {
                'lyricists': [('هالة الزيات', 'Hala El Zayat')],
                'composers': [('محمود الخيامي', 'Mahmoud El Khyami')],
                'arrangers': [('النابلسي', 'El Nabulsi')],
            },
            'أحلى كلام': {
                'lyricists': [('كريم حكيم', 'Karim Hakim')],
                'composers': [('مودي منير', 'Mody Nour')],
                'arrangers': [('Bron Ze', 'Bron Ze')],
            },
            'سجل يا تاريخ': {
                'lyricists': [('تامر حسني', 'Tamer Hosny'), ('عليم', 'Alim')],
                'composers': [('تامر حسني', 'Tamer Hosny'), ('مودي منير', 'Mody Nour')],
                'arrangers': [('النابلسي', 'El Nabulsi')],
            },
            'زي الأيام دي': {
                'lyricists': [('تامر حسني', 'Tamer Hosny')],
                'composers': [('تامر حسني', 'Tamer Hosny')],
                'arrangers': [('النابلسي', 'El Nabulsi')],
            },
            'بُعد مؤقت': {
                'lyricists': [('محمد رمضان', 'Mohamed Ramadan')],
                'composers': [('مودي منير', 'Mody Nour')],
                'arrangers': [('محمود صبري', 'Mahmoud Sabry')],
            },
        }

        created_persons = 0
        created_credits = 0
        skipped_songs = 0

        for song_title, credits_data in song_credits.items():
            song = Song.objects.filter(title_ar=song_title).first()
            if not song:
                self.stdout.write(self.style.WARNING(f'Song not found: {song_title}'))
                skipped_songs += 1
                continue

            self.stdout.write(f'Processing: {song_title}')

            # Add Tamer Hosny as singer
            SongCredit.objects.get_or_create(
                song=song,
                person=tamer_hosny,
                role=SongCredit.Role.SINGER,
            )
            created_credits += 1

            # Add lyricists
            for name_ar, name_en in credits_data.get('lyricists', []):
                person = self._get_or_create_person(name_ar, name_en, Person.Role.POET)
                if person:
                    SongCredit.objects.get_or_create(
                        song=song,
                        person=person,
                        role=SongCredit.Role.LYRICIST,
                    )
                    created_credits += 1

            # Add composers
            for name_ar, name_en in credits_data.get('composers', []):
                person = self._get_or_create_person(name_ar, name_en, Person.Role.COMPOSER)
                if person:
                    SongCredit.objects.get_or_create(
                        song=song,
                        person=person,
                        role=SongCredit.Role.COMPOSER,
                    )
                    created_credits += 1

            # Add arrangers
            for name_ar, name_en in credits_data.get('arrangers', []):
                person = self._get_or_create_person(name_ar, name_en, Person.Role.ARRANGER)
                if person:
                    SongCredit.objects.get_or_create(
                        song=song,
                        person=person,
                        role=SongCredit.Role.ARRANGER,
                    )
                    created_credits += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_persons} persons and {created_credits} credits. '
                f'Skipped {skipped_songs} songs not found in database.'
            )
        )

    def _get_or_create_person(self, name_ar, name_en, role):
        person, created = Person.objects.get_or_create(
            full_name_ar=name_ar,
            defaults={
                'full_name_en': name_en,
                'primary_role': role,
            }
        )
        if created:
            self.stdout.write(f'  Created person: {name_ar}')
            return person
        return person
