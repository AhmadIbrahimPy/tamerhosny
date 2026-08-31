from django.core.management.base import BaseCommand

from backend.media_app.models import Media, MediaCredit
from backend.people_app.models import Person


class Command(BaseCommand):
    help = 'Import cast and crew for Tamer Hosny movies'

    def handle(self, *args, **kwargs):
        # Get Tamer Hosny (assuming he exists with ID 1 or by name)
        tamer_hosny = Person.objects.filter(full_name_ar='تامر حسني').first()
        if not tamer_hosny:
            self.stdout.write(self.style.ERROR('Tamer Hosny not found in database'))
            return

        # Movie credits data
        movie_credits = {
            'حالة حب': {
                'actors': [
                    ('هاني سلامة', 'Hany Salama'),
                    ('هند صبري', 'Hind Sabri'),
                    ('زينة', 'Zeina'),
                    ('شريف رمزي', 'Sherif Ramzy'),
                    ('دنيا عبد العزيز', 'Dunya Abdul Aziz'),
                ],
                'directors': [('سعد هنداوي', 'Saad Hendawi')],
                'screenwriters': [('أحمد عبد الفتاح', 'Ahmed Abdel Fattah')],
            },
            'سيد العاطفي': {
                'actors': [
                    ('عبلة كامل', 'Abla Kamel'),
                    ('نور اللبنانية', 'Nour'),
                    ('زينة', 'Zeina'),
                    ('طلعت زكريا', 'Talat Zakaria'),
                    ('وحيد سيف', 'Wahid Seif'),
                    ('نشوى مصطفى', 'Nashwa Mustafa'),
                    ('لطفي لبيب', 'Lotfy Labib'),
                    ('ضياء الميرغني', 'Diaa El Mirghani'),
                    ('أحمد عقل', 'Ahmed Akl'),
                ],
                'directors': [('علي رجب', 'Ali Ragab')],
                'screenwriters': [('بلال فضل', 'Bilal Fadl')],
            },
            'عمر وسلمى': {
                'actors': [
                    ('مي عز الدين', 'Mai Ezz El-Din'),
                    ('ميس حمدان', 'Mays Hamdan'),
                    ('عزت أبو عوف', 'Ezzat Abu Ouf'),
                    ('مروة عبد المنعم', 'Marwa Abdel Moneim'),
                    ('رامي وحيد', 'Ramy Wahid'),
                ],
                'directors': [('أكرم فريد', 'Akram Farid')],
                'screenwriters': [
                    ('تامر حسني', 'Tamer Hosny'),
                    ('أحمد عبد الفتاح', 'Ahmed Abdel Fattah'),
                ],
            },
            'كابتن هيما': {
                'actors': [
                    ('زينة', 'Zeina'),
                    ('أحمد راتب', 'Ahmed Rateb'),
                    ('أحمد زاهر', 'Ahmed Zaher'),
                    ('ميار الغيطي', 'Mayar El Gheity'),
                    ('عبد الله مشرف', 'Abdullah Meshref'),
                    ('مروة عبد المنعم', 'Marwa Abdel Moneim'),
                    ('محسن منصور', 'Mohsen Mansour'),
                    ('يوسف عيد', 'Youssef Eid'),
                    ('دنيا عبد العزيز', 'Dunya Abdul Aziz'),
                    ('ليلى أحمد زاهر', 'Laila Ahmed Zaher'),
                    ('ملك أحمد زاهر', 'Malak Ahmed Zaher'),
                ],
                'directors': [('نصر محروس', 'Nasr Mahrous')],
                'screenwriters': [
                    ('نصر محروس', 'Nasr Mahrous'),
                    ('أحمد عبد الفتاح', 'Ahmed Abdel Fattah'),
                ],
            },
            'عمر وسلمى 2': {
                'actors': [
                    ('مي عز الدين', 'Mai Ezz El-Din'),
                    ('عزت أبو عوف', 'Ezzat Abu Ouf'),
                    ('ميرهان حسين', 'Merihan Hussein'),
                    ('مروة عبد المنعم', 'Marwa Abdel Moneim'),
                    ('ملك أحمد زاهر', 'Malak Ahmed Zaher'),
                    ('ليلى أحمد زاهر', 'Laila Ahmed Zaher'),
                    ('نهلة زكي', 'Nehla Zaki'),
                    ('رضا حامد', 'Reda Hamed'),
                    ('ميسرة', 'Mesra'),
                    ('مجدي بدر', 'Magdy Badr'),
                    ('داليا بدر', 'Dalia Badr'),
                    ('كريم محسن', 'Karim Mohsen'),
                ],
                'directors': [('أحمد البدري', 'Ahmed El Badri')],
                'screenwriters': [
                    ('تامر حسني', 'Tamer Hosny'),
                    ('أحمد عبد الفتاح', 'Ahmed Abdel Fattah'),
                ],
            },
            'نور عيني': {
                'actors': [
                    ('منة شلبي', 'Menna Shalabi'),
                    ('عمرو يوسف', 'Amr Youssef'),
                    ('عبير صبري', 'Abeer Sabry'),
                    ('منة فضالي', 'Menna Fadali'),
                    ('مروة عبد المنعم', 'Marwa Abdel Moneim'),
                    ('إسلام جمال', 'Islam Gamal'),
                    ('سعيد عبد الغني', 'Saeed Abdel Ghani'),
                    ('كريم محسن', 'Karim Mohsen'),
                    ('حسام الحسيني', 'Hossam El Husseiny'),
                    ('رضا إدريس', 'Reda Idris'),
                    ('رضا حامد', 'Reda Hamed'),
                    ('ريم صابوني', 'Rim Sabouni'),
                    ('ريم رأفت', 'Rim Raafat'),
                ],
                'directors': [('وائل إحسان', 'Wael Ehsan')],
                'screenwriters': [
                    ('تامر حسني', 'Tamer Hosny'),
                    ('أحمد عبد الفتاح', 'Ahmed Abdel Fattah'),
                ],
            },
            'عمر وسلمى 3': {
                'actors': [
                    ('مي عز الدين', 'Mai Ezz El-Din'),
                    ('عزت أبو عوف', 'Ezzat Abu Ouf'),
                ],
                'directors': [('محمد سامي', 'Mohamed Samy')],
                'screenwriters': [
                    ('تامر حسني', 'Tamer Hosny'),
                    ('أحمد عبد الفتاح', 'Ahmed Abdel Fattah'),
                ],
            },
            'أهواك': {
                'actors': [
                    ('غادة عادل', 'Ghada Adel'),
                    ('إنتصار', 'Entessar'),
                    ('محمود حميدة', 'Mahmoud Hemida'),
                    ('أمل رزق', 'Amal Rezk'),
                    ('أحمد مالك', 'Ahmed Malek'),
                    ('إلهام عبد البديع', 'Elham Abdelbadea'),
                    ('سعاد القاضي', 'Soad Al-Kadi'),
                ],
                'directors': [('محمد سامي', 'Mohamed Samy')],
                'screenwriters': [
                    ('تامر حسني', 'Tamer Hosny'),
                    ('وليد يوسف', 'Walid Youssef'),
                ],
            },
            'تصبح على خير': {
                'actors': [
                    ('نور', 'Nour'),
                    ('درة', 'Dorra'),
                    ('مي عمر', 'Mai Omar'),
                    ('محمود البزاوي', 'Mahmoud El Bazzawy'),
                    ('بدرية طلبة', 'Badria Talal'),
                ],
                'directors': [('محمد سامي', 'Mohamed Samy')],
                'screenwriters': [('تامر حسني', 'Tamer Hosny')],
            },
            'البدلة': {
                'actors': [
                    ('أكرم حسني', 'Akram Hosny'),
                    ('أمينة خليل', 'Amina Khalil'),
                    ('ماجد المصري', 'Magdy El Masry'),
                    ('دلال عبد العزيز', 'Dalal Abdul Aziz'),
                    ('محمود البزاوي', 'Mahmoud El Bazzawy'),
                    ('طاهر أبو ليلة', 'Taher Abu Leila'),
                    ('محمد علاء', 'Mohamed Alaa'),
                    ('سلوى محمد علي', 'Salwa Mohamed Ali'),
                    ('ياسر علي ماهر', 'Yasser Ali Maher'),
                ],
                'directors': [('محمد جمال العدل', 'Mohamed Gamal El Adl')],
                'screenwriters': [
                    ('تامر حسني', 'Tamer Hosny'),
                    ('أيمن بهجت قمر', 'Ayman Bahgat Qamar'),
                ],
            },
            'الفلوس': {
                'actors': [
                    ('زينة', 'Zeina'),
                    ('خالد الصاوي', 'Khaled El Sawy'),
                    ('عائشة بن أحمد', 'Aisha Ben Ahmed'),
                    ('محمد سلام', 'Mohamed Sallam'),
                    ('كميل سلامة', 'Camille Salameh'),
                ],
                'directors': [('سعيد الماروق', 'Said Marouk')],
                'screenwriters': [
                    ('تامر حسني', 'Tamer Hosny'),
                    ('محمد عبد المعطي', 'Mohamed Abdel Moaty'),
                ],
            },
            'مش أنا': {
                'actors': [
                    ('حلا شيحة', 'Hala Shiha'),
                    ('ماجد الكدواني', 'Magdy El Kadwany'),
                    ('حجاج عبد العظيم', 'Hegazy Abdel Azim'),
                    ('سوسن بدر', 'Sousan Badr'),
                    ('إياد نصار', 'Eyad Nassar'),
                    ('عصام السقا', 'Essam El Sakka'),
                    ('محمد عبد الرحمن', 'Mohamed Abdel Rahman'),
                    ('فايز المالكي', 'Fayez Al Malki'),
                ],
                'directors': [('سارة وفيق', 'Sara Wafiq')],
                'screenwriters': [('تامر حسني', 'Tamer Hosny')],
            },
            'بحبك': {
                'actors': [
                    ('هنا الزاهد', 'Hana El Zahed'),
                    ('حمدي الميرغني', 'Hamdy El Mergheny'),
                    ('هدى المفتي', 'Hoda El Mufti'),
                    ('مدحت تيخا', 'Medhat Teykha'),
                    ('شهد الشاطر', 'Shahd El Shater'),
                    ('عالية راشد', 'Aalia Rashid'),
                    ('تميم عبده', 'Tarek Ebeid'),
                    ('فرح الزاهد', 'Farah El Zahed'),
                ],
                'directors': [('تامر حسني', 'Tamer Hosny')],
                'screenwriters': [('تامر حسني', 'Tamer Hosny')],
            },
            'تاج': {
                'actors': [
                    ('دينا الشربيني', 'Dina El Sherbiny'),
                    ('هالة فاخر', 'Hala Fakher'),
                    ('عمرو عبد الجليل', 'Amr Abdel Galil'),
                    ('ساندي', 'Sandy'),
                    ('حمد فتحي أبو الريش', 'Hamed Fathy Abu El Reesh'),
                    ('أحمد بدير', 'Ahmed Bedier'),
                    ('محمد أبو داود', 'Mohamed Abu Dawood'),
                    ('محمد الجوهري', 'Mohamed El Gohary'),
                    ('أحمد ثابت', 'Ahmed Thabet'),
                    ('إحسان الترك', 'Ihsan El Turk'),
                    ('ليلى عز العرب', 'Laila Ezz El Arab'),
                ],
                'directors': [('سارة وفيق', 'Sara Wafiq')],
                'screenwriters': [('تامر حسني', 'Tamer Hosny')],
            },
            'ريستارت': {
                'actors': [
                    ('هنا الزاهد', 'Hana El Zahed'),
                    ('باسم سمرة', 'Bassem Samra'),
                    ('محمد ثروت', 'Mohamed Tharwat'),
                    ('عصام السقا', 'Essam El Sakka'),
                    ('ميمي جمال', 'Mimi Gamal'),
                    ('إلهام شاهين', 'Elham Shahin'),
                    ('محمد رجب', 'Mohamed Ragab'),
                    ('شيماء سيف', 'Shaimaa Seif'),
                    ('أحمد حسام', 'Ahmed Hossam'),
                    ('رانيا منصور', 'Rania Mansour'),
                ],
                'directors': [('سارة وفيق', 'Sara Wafiq')],
                'screenwriters': [
                    ('تامر حسني', 'Tamer Hosny'),
                    ('أيمن بهجت قمر', 'Ayman Bahgat Qamar'),
                ],
            },
        }

        created_persons = 0
        created_credits = 0

        for movie_title, credits_data in movie_credits.items():
            movie = Media.objects.filter(title_ar=movie_title, media_type='MOVIE').first()
            if not movie:
                self.stdout.write(self.style.WARNING(f'Movie not found: {movie_title}'))
                continue

            self.stdout.write(f'Processing: {movie_title}')

            # Add Tamer Hosny as actor
            MediaCredit.objects.get_or_create(
                media=movie,
                person=tamer_hosny,
                role=MediaCredit.Role.ACTOR,
                defaults={'character_name': ''}
            )
            created_credits += 1

            # Add actors
            for name_ar, name_en in credits_data.get('actors', []):
                person = self._get_or_create_person(name_ar, name_en, Person.Role.ACTOR)
                if person:
                    MediaCredit.objects.get_or_create(
                        media=movie,
                        person=person,
                        role=MediaCredit.Role.ACTOR,
                        defaults={'character_name': ''}
                    )
                    created_credits += 1

            # Add directors
            for name_ar, name_en in credits_data.get('directors', []):
                person = self._get_or_create_person(name_ar, name_en, Person.Role.DIRECTOR)
                if person:
                    MediaCredit.objects.get_or_create(
                        media=movie,
                        person=person,
                        role=MediaCredit.Role.DIRECTOR,
                        defaults={'character_name': ''}
                    )
                    created_credits += 1

            # Add screenwriters
            for name_ar, name_en in credits_data.get('screenwriters', []):
                person = self._get_or_create_person(name_ar, name_en, Person.Role.SCREENWRITER)
                if person:
                    MediaCredit.objects.get_or_create(
                        media=movie,
                        person=person,
                        role=MediaCredit.Role.SCREENWRITER,
                        defaults={'character_name': ''}
                    )
                    created_credits += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_persons} persons and {created_credits} credits'
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
