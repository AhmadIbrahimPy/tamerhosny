from django.core.management.base import BaseCommand

from backend.music_app.models import Album, Song, SongCredit
from backend.people_app.models import Person


class Command(BaseCommand):
    help = 'Import songs and credits for Tamer Hosny albums'

    def handle(self, *args, **kwargs):
        # Get Tamer Hosny
        tamer_hosny = Person.objects.filter(full_name_ar='تامر حسني').first()
        if not tamer_hosny:
            self.stdout.write(self.style.ERROR('Tamer Hosny not found in database'))
            return

        # Complete album data with songs and credits
        albums_data = {
            'مش هتكرر': {
                'year': 2026,
                'songs': [
                    {
                        'title_ar': 'بنت مين',
                        'title_en': 'Bent Men',
                        'lyricists': [('أمير طعيمة', 'Amer Taaema')],
                        'composers': [('عمرو مصطفى', 'Amr Mostafa')],
                        'arrangers': [('عادل حقي', 'Adel Haki')],
                    },
                    {
                        'title_ar': 'وش الخير',
                        'title_en': 'Wosh El Kheir',
                        'lyricists': [('تامر حسني', 'Tamer Hosny'), ('عبد المنعم طه', 'Abdel Monem Taher')],
                        'composers': [('تامر حسني', 'Tamer Hosny'), ('كريم محسن', 'Karim Mohsen')],
                        'arrangers': [('النابلسي', 'El Nabulsi')],
                    },
                    {
                        'title_ar': 'يا خسارتنا',
                        'title_en': 'Ya Khasartna',
                        'lyricists': [('تامر حسين', 'Tamer Hussein')],
                        'composers': [('عمرو مصطفى', 'Amr Mostafa')],
                        'arrangers': [('أحمد عادل', 'Ahmed Adel')],
                    },
                    {
                        'title_ar': 'ما تيجي',
                        'title_en': 'Ma Teigi',
                        'lyricists': [('بلال سرور', 'Bilal Sarour')],
                        'composers': [('بلال سرور', 'Bilal Sarour')],
                        'arrangers': [('Kay Music', 'Kay Music')],
                    },
                    {
                        'title_ar': 'مولعينها',
                        'title_en': 'Molaeenha',
                        'lyricists': [('مصطفى حدوتة', 'Mostafa Hadouta')],
                        'composers': [('إيهاب عبد الواحد', 'Ehab Abdel Wahed')],
                        'arrangers': [('كوليبكس', 'Colibex')],
                    },
                    {
                        'title_ar': 'عايزك توعديني',
                        'title_en': 'Ayzeek Tawadani',
                        'lyricists': [('أمير طعيمة', 'Amer Taaema')],
                        'composers': [('عمرو مصطفى', 'Amr Mostafa')],
                        'arrangers': [('عمرو مصطفى', 'Amr Mostafa'), ('تامر حسني', 'Tamer Hosny')],
                    },
                    {
                        'title_ar': 'قال فاكرني',
                        'title_en': 'Gal Fekrni',
                        'lyricists': [('مصطفى ناصر', 'Mostafa Naser')],
                        'composers': [('محمد يحيى', 'Mohamed Yehia')],
                        'arrangers': [('إلهامي دهيمة', 'Elhamy Dehima'), ('أحمد حسام', 'Ahmed Hossam')],
                    },
                    {
                        'title_ar': 'مش هتكرر',
                        'title_en': 'Mosh Hatkarar',
                        'lyricists': [('محمد يحيى', 'Mohamed Yehia')],
                        'composers': [('محمد يحيى', 'Mohamed Yehia')],
                        'arrangers': [('خالد نبيل', 'Khaled Nabil')],
                    },
                    {
                        'title_ar': 'في القلب إنت',
                        'title_en': 'Fi El Alb Enta',
                        'lyricists': [('تامر حسين', 'Tamer Hussein')],
                        'composers': [('عزيز الشافعي', 'Aziz El Shafei')],
                        'arrangers': [('حسام الصعبي', 'Hossam El Saabi')],
                    },
                    {
                        'title_ar': 'ماتمشيش',
                        'title_en': 'Matmashish',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                    },
                    {
                        'title_ar': 'بعيش على الذكرى',
                        'title_en': 'Baesh Ala El Zekra',
                        'lyricists': [('أمير طعيمة', 'Amer Taaema')],
                        'composers': [('عمرو مصطفى', 'Amr Mostafa')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                    {
                        'title_ar': 'دهب قشرة',
                        'title_en': 'Dahab Qashra',
                        'lyricists': [('ڤانتا', 'Vanta')],
                        'composers': [('محمد يحيى', 'Mohamed Yehia')],
                        'arrangers': [('يحيى يوسف', 'Yahya Youssef')],
                    },
                    {
                        'title_ar': 'متأثر بغيابه',
                        'title_en': 'Motaathar Be Ghiabo',
                        'lyricists': [('تامر حسين', 'Tamer Hussein')],
                        'composers': [('عزيز الشافعي', 'Aziz El Shafei')],
                        'arrangers': [('جلال حمداوي', 'Galal Hamdawi')],
                    },
                    {
                        'title_ar': 'اتحامى فيا',
                        'title_en': 'Etahamy Fea',
                        'lyricists': [('تامر حسني', 'Tamer Hosny'), ('أحمد المالكي', 'Ahmed El Malki')],
                        'composers': [('تامر حسني', 'Tamer Hosny'), ('محمد يحيى', 'Mohamed Yehia')],
                        'arrangers': [('أحمد عبد السلام', 'Ahmed Abdel Salam')],
                    },
                ],
            },
            'لينا معاد': {
                'year': 2025,
                'songs': [
                    {
                        'title_ar': 'الاحتياج وحش',
                        'title_en': 'El Ehtiyag Wahsh',
                        'lyricists': [('محمد القاياتي', 'Mohamed El Qayati')],
                        'composers': [('بلال سرور', 'Bilal Sarour')],
                        'arrangers': [('علي فتح الله', 'Ali Fathallah')],
                    },
                    {
                        'title_ar': 'الأنوثة الطاغية',
                        'title_en': 'El Onotha El Taghia',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('وسام محمد', 'Wessam Mohamed')],
                    },
                    {
                        'title_ar': 'لينا معاد',
                        'title_en': 'Lena Mead',
                        'lyricists': [('تامر حسني', 'Tamer Hosny'), ('شريف مكاوي', 'Sherif Makawi')],
                        'composers': [('شريف مكاوي', 'Sherif Makawi')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                    },
                    {
                        'title_ar': 'الذوق العالي',
                        'title_en': 'El Thoq El Ali',
                        'lyricists': [('تامر حسين', 'Tamer Hussein')],
                        'composers': [('محمد رحيم', 'Mohamed Rahim')],
                        'arrangers': [('أحمد طارق يحيى', 'Ahmed Tarek Yehia')],
                        'featured_artists': [('محمد منير', 'Mohamed Mounir')],
                    },
                    {
                        'title_ar': 'حبيبي تقلان',
                        'title_en': 'Habibi Talan',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('علي فتح الله', 'Ali Fathallah')],
                    },
                    {
                        'title_ar': 'يا حب',
                        'title_en': 'Ya Hob',
                        'lyricists': [('ملاك عادل', 'Malak Adel')],
                        'composers': [('محمد يحيى', 'Mohamed Yehia')],
                        'arrangers': [('أحمد عبد السلام', 'Ahmed Abdel Salam')],
                    },
                    {
                        'title_ar': 'مستني إيه',
                        'title_en': 'Mostani Eih',
                        'lyricists': [('عليم', 'Alim')],
                        'composers': [('سام محمد', 'Samed Mohamed')],
                        'arrangers': [('أحمد عبد السلام', 'Ahmed Abdel Salam')],
                    },
                    {
                        'title_ar': 'واحشني يابن اللذينة',
                        'title_en': 'Wahasni Ya Ben El Lazina',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('النابلسي', 'El Nabulsi')],
                    },
                    {
                        'title_ar': 'حبك لو غلطة',
                        'title_en': 'Hobbak Law Ghalta',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                    },
                    {
                        'title_ar': 'يالا يا كداب',
                        'title_en': 'Yalla Ya Kadab',
                        'lyricists': [('تامر حسني', 'Tamer Hosny'), ('عمر عبده', 'Omar Abdu')],
                        'composers': [('عمرو الشاذلي', 'Amro El Shazly')],
                        'arrangers': [('محمد ياسر', 'Mohamed Yasser')],
                    },
                    {
                        'title_ar': 'خلونا نشوفكم تاني',
                        'title_en': 'Kholona Neshoufak Tani',
                        'lyricists': [('محمود أنور', 'Mahmoud Anwar')],
                        'composers': [('محمود أنور', 'Mahmoud Anwar')],
                        'arrangers': [('محمد مجدي', 'Mohamed Magdi')],
                    },
                    {
                        'title_ar': 'هو ده بقى',
                        'title_en': 'Howa Da Baqa',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                    },
                    {
                        'title_ar': 'الذوق العالي',
                        'title_en': 'El Thoq El Ali',
                        'lyricists': [('تامر حسين', 'Tamer Hussein')],
                        'composers': [('محمد رحيم', 'Mohamed Rahim')],
                        'arrangers': [('أحمد طارق يحيى', 'Ahmed Tarek Yehia')],
                        'featured_artists': [('محمد منير', 'Mohamed Mounir')],
                    },
                    {
                        'title_ar': 'ملكة جمال الكون',
                        'title_en': 'Malikat Gamal El Kawn',
                        'lyricists': [('تامر حسني', 'Tamer Hosny'), ('الشامي', 'El Shamy')],
                        'composers': [('تامر حسني', 'Tamer Hosny'), ('الشامي', 'El Shamy')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                        'featured_artists': [('الشامي', 'El Shamy')],
                    },
                ],
            },
            'عشأنجي': {
                'year': 2022,
                'songs': [
                    {
                        'title_ar': 'عشأنجي',
                        'title_en': 'Eshangi',
                        'lyricists': [('حمادة السيد', 'Hamada El Sayed')],
                        'composers': [('مديح', 'Medih')],
                        'arrangers': [('أمير محروس', 'Amir Mahrous')],
                    },
                    {
                        'title_ar': 'مابجيش بالطريقة دي',
                        'title_en': 'Mabgesh Bel Tariqa Di',
                        'lyricists': [('تامر حسين', 'Tamer Hussein')],
                        'composers': [('تامر علي', 'Tamer Ali')],
                        'arrangers': [('يحيى يوسف', 'Yahya Youssef')],
                    },
                    {
                        'title_ar': 'سوحنا',
                        'title_en': 'Sawhna',
                        'lyricists': [('محمد عاطف', 'Mohamed Atef')],
                        'composers': [('أحمد زعيم', 'Ahmed Zaeem')],
                        'arrangers': [('وسام عبد المنعم', 'Wessam Abdel Monem')],
                    },
                    {
                        'title_ar': 'خدنا مناعة',
                        'title_en': 'Khodna Manaa',
                        'lyricists': [('أحمد المالكي', 'Ahmed El Malki')],
                        'composers': [('بلال سرور', 'Bilal Sarour')],
                        'arrangers': [('توما', 'Toma')],
                    },
                    {
                        'title_ar': 'ليه طلة',
                        'title_en': 'Leih Talla',
                        'lyricists': [('هالة الزيات', 'Hala El Zayat')],
                        'composers': [('محمود الخيامي', 'Mahmoud El Khyami')],
                        'arrangers': [('النابلسي', 'El Nabulsi')],
                    },
                    {
                        'title_ar': 'أحلى كلام',
                        'title_en': 'Ahla Kalam',
                        'lyricists': [('كريم حكيم', 'Karim Hakim')],
                        'composers': [('مودي منير', 'Mody Nour')],
                        'arrangers': [('Bron Ze', 'Bron Ze')],
                    },
                    {
                        'title_ar': 'سجل يا تاريخ',
                        'title_en': 'Sagel Ya Tarekh',
                        'lyricists': [('تامر حسني', 'Tamer Hosny'), ('عليم', 'Alim')],
                        'composers': [('تامر حسني', 'Tamer Hosny'), ('مودي منير', 'Mody Nour')],
                        'arrangers': [('النابلسي', 'El Nabulsi')],
                    },
                    {
                        'title_ar': 'زي الأيام دي',
                        'title_en': 'Zy El Ayam Di',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('النابلسي', 'El Nabulsi')],
                    },
                    {
                        'title_ar': 'بُعد مؤقت',
                        'title_en': 'Bod Muwaqat',
                        'lyricists': [('محمد رمضان', 'Mohamed Ramadan')],
                        'composers': [('مودي منير', 'Mody Nour')],
                        'arrangers': [('محمود صبري', 'Mahmoud Sabry')],
                    },
                ],
            },
            'خليك فولاذي': {
                'year': 2020,
                'songs': [
                    {
                        'title_ar': 'اختراع',
                        'title_en': 'Ekhteraa',
                        'lyricists': [('أحمد حسن راؤول', 'Ahmed Hassan Raoul')],
                        'composers': [('أحمد زعيم', 'Ahmed Zaeem')],
                        'arrangers': [('وسام عبد المنعم', 'Wessam Abdel Monem')],
                        'featured_artists': [('محمود العسيلي', 'Mahmoud El Assaily')],
                    },
                    {
                        'title_ar': 'مبطلناش إحساس',
                        'title_en': 'Mabtelnash Ehsas',
                        'lyricists': [('محمد القاياتي', 'Mohamed El Qayati')],
                        'composers': [('محمد حمزة', 'Mohamed Hamza')],
                        'arrangers': [('أمين نبيل', 'Amin Nabil')],
                    },
                    {
                        'title_ar': 'فجأة افترقنا',
                        'title_en': 'Fojaa Eftarqna',
                        'lyricists': [('محمد عاطف', 'Mohamed Atef')],
                        'composers': [('تامر علي', 'Tamer Ali')],
                        'arrangers': [('يحيى يوسف', 'Yahya Youssef')],
                    },
                    {
                        'title_ar': 'بألف سلامة',
                        'title_en': 'Baalf Salama',
                        'lyricists': [('تامر حسين', 'Tamer Hussein')],
                        'composers': [('محمد يحيى', 'Mohamed Yehia')],
                        'arrangers': [('يحيى يوسف', 'Yahya Youssef')],
                    },
                    {
                        'title_ar': 'قوِّلني كلام',
                        'title_en': 'Golni Kalam',
                        'lyricists': [('تامر حسين', 'Tamer Hussein')],
                        'composers': [('تامر علي', 'Tamer Ali')],
                        'arrangers': [('علي فتح الله', 'Ali Fathallah')],
                    },
                    {
                        'title_ar': 'كرهتني في الحب',
                        'title_en': 'Krahatni Fi El Hob',
                        'lyricists': [('محمد البوغه', 'Mohamed El Bogha')],
                        'composers': [('محمود الخيامي', 'Mahmoud El Khyami')],
                        'arrangers': [('طارق عبد الجابر', 'Tarek Abdel Gaber')],
                    },
                    {
                        'title_ar': 'في جمال كده',
                        'title_en': 'Fi Gamal Keda',
                        'lyricists': [('حسام سعيد', 'Hossam Saeed')],
                        'composers': [('محمود أنور', 'Mahmoud Anwar')],
                        'arrangers': [('جلال حمداوي', 'Galal Hamdawi')],
                    },
                    {
                        'title_ar': 'نفس النهاية',
                        'title_en': 'Nafs El Nehaya',
                        'lyricists': [('أحمد المالكي', 'Ahmed El Malki')],
                        'composers': [('مدين', 'Madin')],
                        'arrangers': [('أحمد عبد السلام', 'Ahmed Abdel Salam')],
                    },
                    {
                        'title_ar': 'طمعتيني',
                        'title_en': 'Tamatini',
                        'lyricists': [('بلال سرور', 'Bilal Sarour')],
                        'composers': [('بلال سرور', 'Bilal Sarour')],
                        'arrangers': [('هاني ربيع', 'Hani Rabie')],
                    },
                    {
                        'title_ar': 'قد الفراق',
                        'title_en': 'Qad El Firaq',
                        'lyricists': [('تامر حسين', 'Tamer Hussein')],
                        'composers': [('إسلام زكي', 'Islam Zaki')],
                        'arrangers': [('إسلام زكي', 'Islam Zaki')],
                    },
                    {
                        'title_ar': 'خليك فولاذي',
                        'title_en': 'Khalik Foladi',
                        'lyricists': [('عزيز الشافعي', 'Aziz El Shafei')],
                        'composers': [('عزيز الشافعي', 'Aziz El Shafei')],
                        'arrangers': [('رامي سمير', 'Ramy Sameer')],
                    },
                ],
            },
            'عيش بشوقك': {
                'year': 2018,
                'songs': [
                    {
                        'title_ar': 'لولاك حبيبي',
                        'title_en': 'Lolak Habibi',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('جلال الحمداوي', 'Galal Hamdawi')],
                    },
                    {
                        'title_ar': 'قابلتيني',
                        'title_en': 'Qabaltini',
                        'lyricists': [('تامر حسين', 'Tamer Hussein')],
                        'composers': [('تامر علي', 'Tamer Ali')],
                        'arrangers': [('هيثم راضي', 'Hitham Radi')],
                    },
                    {
                        'title_ar': 'ناسيني ليه',
                        'title_en': 'Nasini Leih',
                        'lyricists': [('تامر حسين', 'Tamer Hussein')],
                        'composers': [('تامر علي', 'Tamer Ali')],
                        'arrangers': [('وسام عبد المنعم', 'Wessam Abdel Monem')],
                    },
                    {
                        'title_ar': 'كفاياك اعذار',
                        'title_en': 'Kafayak Aazar',
                        'lyricists': [('هاني أبو النجا', 'Hani Abu El Naga')],
                        'composers': [('تامر علي', 'Tamer Ali')],
                        'arrangers': [('يحيى يوسف', 'Yahya Youssef')],
                    },
                    {
                        'title_ar': 'عيش بشوقك',
                        'title_en': 'Eish Beshoak',
                        'lyricists': [('مصطفي حسن', 'Mostafa Hassan')],
                        'composers': [('بلال سرور', 'Bilal Sarour')],
                        'arrangers': [('هاني محروس', 'Hani Mahrous'), ('بلال سرور', 'Bilal Sarour')],
                    },
                    {
                        'title_ar': 'وأخيراً',
                        'title_en': 'Wa Akhiran',
                        'lyricists': [('عبد الرحمن شوقي', 'Abdel Rahman Shokry')],
                        'composers': [('عبد الرحمن شوقي', 'Abdel Rahman Shokry')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                    },
                    {
                        'title_ar': 'وإنت معايا',
                        'title_en': 'Wa Enta Maaya',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('جلال الحمداوي', 'Galal Hamdawi')],
                        'featured_artists': [('الشاب خالد', 'Cheb Khaled')],
                    },
                    {
                        'title_ar': 'حكايات الحب',
                        'title_en': 'Hekayat El Hob',
                        'lyricists': [('صابر كمال', 'Saber Kamal')],
                        'composers': [('محمد عبيه', 'Mohamed Abeih')],
                        'arrangers': [('محمد العشي', 'Mohamed El Ashy')],
                    },
                    {
                        'title_ar': 'تمن إختيار',
                        'title_en': 'Tamem Ekhtiar',
                        'lyricists': [('صابر كمال', 'Saber Kamal')],
                        'composers': [('شريف بدر', 'Sherif Badr')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                    },
                    {
                        'title_ar': 'ورد صناعي',
                        'title_en': 'Werd Sanaei',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('محمد يحيى', 'Mohamed Yehia')],
                        'arrangers': [('أماديو', 'Amadeo')],
                    },
                    {
                        'title_ar': 'ولا يوم من أيامه',
                        'title_en': 'Wla Youm Men Ayamo',
                        'lyricists': [('ياسين جمال', 'Yassin Gamal')],
                        'composers': [('علي شعبان', 'Ali Shaban')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': '100 وش',
                        'title_en': '100 Wash',
                        'lyricists': [('تامر حسني', 'Tamer Hosny'), ('رمضان محمد', 'Ramadan Mohamed')],
                        'composers': [('تامر حسني', 'Tamer Hosny'), ('محمد الصاوي', 'Mohamed El Sawy')],
                        'arrangers': [('أحمد عادل', 'Ahmed Adel')],
                        'featured_artists': [('أحمد شيبة', 'Ahmed Sheiba'), ('دياب', 'Diab'), ('مصطفى حجاج', 'Mostafa Hagag')],
                    },
                    {
                        'title_ar': 'حلم سنين',
                        'title_en': 'Helm Senin',
                        'lyricists': [('تامر حسين', 'Tamer Hussein')],
                        'composers': [('تامر علي', 'Tamer Ali')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                ],
            },
            'عمرى ابتدا': {
                'year': 2016,
                'songs': [
                    {
                        'title_ar': 'يا مالي عيني',
                        'title_en': 'Ya Mali Aini',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('عبد الرحمن شوقي', 'Abdel Rahman Shokry')],
                        'arrangers': [('جلال الحمداوي', 'Galal Hamdawi')],
                    },
                    {
                        'title_ar': 'نفس الحنين',
                        'title_en': 'Nafs El Haneen',
                        'lyricists': [('جمال الخولي', 'Gamal El Khouly')],
                        'composers': [('محمد يحيى', 'Mohamed Yehia')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'إحساسى مبيكدبش',
                        'title_en': 'Ehsasi Mibkadbish',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('هيثم راضي', 'Hitham Radi')],
                    },
                    {
                        'title_ar': 'شكراً انك في حياتى',
                        'title_en': 'Shokran Enak Fi Hayati',
                        'lyricists': [('تامر حسني', 'Tamer Hosny'), ('ايمن عزمي', 'Ayman Azmy')],
                        'composers': [('شريف بدر', 'Sherif Badr')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'رحلة حياة',
                        'title_en': 'Rehla Hayat',
                        'lyricists': [('ايمن بهجت قمر', 'Ayman Bahgat Qamar')],
                        'composers': [('وليد سعد', 'Walid Saad')],
                        'arrangers': [('احمد ابراهيم', 'Ahmed Ibrahim')],
                    },
                    {
                        'title_ar': 'عمري إبتدا',
                        'title_en': 'Omri Ebtda',
                        'lyricists': [('سلامة علي', 'Salama Ali')],
                        'composers': [('شريف بدر', 'Sherif Badr')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'كداب وأناني',
                        'title_en': 'Kadab Wa Anani',
                        'lyricists': [('أمير طعيمة', 'Amer Taaema')],
                        'composers': [('تامر عاشور', 'Tamer Ashour')],
                        'arrangers': [('طارق مدكور', 'Tarek Madkour')],
                    },
                    {
                        'title_ar': 'يا بعيد',
                        'title_en': 'Ya Baeed',
                        'lyricists': [('نادر عبد الله', 'Nader Abdallah')],
                        'composers': [('تامر علي', 'Tamer Ali')],
                        'arrangers': [('ياسر ماجد', 'Yasser Magdi')],
                    },
                    {
                        'title_ar': 'كان في واحدة',
                        'title_en': 'Kan Fi Wahda',
                        'lyricists': [('سلامة علي', 'Salama Ali')],
                        'composers': [('محمد يحيى', 'Mohamed Yehia')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'فاض بيا',
                        'title_en': 'Fad Biya',
                        'lyricists': [('حسن مهران', 'Hassan Mehran')],
                        'composers': [('تامر علي', 'Tamer Ali')],
                        'arrangers': [('يحيى يوسف', 'Yahya Youssef')],
                    },
                    {
                        'title_ar': 'الحارس الله',
                        'title_en': 'El Haras Allah',
                        'lyricists': [('سلامة علي', 'Salama Ali')],
                        'composers': [('شريف بدر', 'Sherif Badr')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'حبيبي خلاص',
                        'title_en': 'Habibi Khalas',
                        'lyricists': [('محمد مصطفى مالك', 'Mohamed Mostafa Malik')],
                        'composers': [('محمود انور', 'Mahmoud Anwar')],
                        'arrangers': [('الهامي دهيمة', 'Elhamy Dehima')],
                    },
                    {
                        'title_ar': 'يا عيون',
                        'title_en': 'Ya Ayoun',
                        'lyricists': [('احمد المالكي', 'Ahmed El Malki')],
                        'composers': [('شريف بدر', 'Sherif Badr')],
                        'arrangers': [('تومـا', 'Toma')],
                    },
                    {
                        'title_ar': 'بطلة العالم في النكد',
                        'title_en': 'Batlet El Alam Fi El Nakd',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('عبد الرحمن شوقي', 'Abdel Rahman Shokry')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                ],
            },
            'هرمون السعاده': {
                'year': 2024,
                'songs': [
                    {
                        'title_ar': 'هرمون السعادة',
                        'title_en': 'Hormone El Saada',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                    },
                    {
                        'title_ar': 'مش هتغير عشان حد',
                        'title_en': 'Mosh Hatghayarshan Hadd',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                    },
                    {
                        'title_ar': 'معلش',
                        'title_en': 'Mollesh',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('معاذ', 'Moaz')],
                        'featured_artists': [('زاب ثروت', 'Zap Tharwat')],
                    },
                    {
                        'title_ar': 'موحشتكي',
                        'title_en': 'Mowahashtekish',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                    },
                    {
                        'title_ar': 'موضوع رجوعنا',
                        'title_en': 'Mawdoo Regoona',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                    },
                    {
                        'title_ar': 'ولا يهمك',
                        'title_en': 'Wla Yhemmak',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                    },
                    {
                        'title_ar': '30 حياة',
                        'title_en': '30 Hayat',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                        'featured_artists': [('مهى فتوني', 'Maha Ftouni')],
                    },
                    {
                        'title_ar': 'تاج',
                        'title_en': 'Taj',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                    },
                ],
            },
            '180 درجة': {
                'year': 2014,
                'songs': [
                    {
                        'title_ar': 'مين ممكن',
                        'title_en': 'Men Momkin',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('نور', 'Nour')],
                    },
                    {
                        'title_ar': 'ده انا بابا',
                        'title_en': 'Da Ana Baba',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('عبد الرحمن شوقي', 'Abdel Rahman Shokry')],
                    },
                    {
                        'title_ar': 'كل ده على ايه',
                        'title_en': 'Kol Da Ala Eih',
                        'lyricists': [('أمير طعيمة', 'Amer Taaema')],
                        'composers': [('شريف بدر', 'Sherif Badr')],
                        'arrangers': [('شريف مكاوي', 'Sherif Makawi')],
                    },
                    {
                        'title_ar': '180 درجة',
                        'title_en': '180 Degree',
                        'lyricists': [('محمد عاطف', 'Mohamed Atef')],
                        'composers': [('رامي جمال', 'Ramy Gamal')],
                        'arrangers': [('أحمد إبراهيم', 'Ahmed Ibrahim')],
                    },
                    {
                        'title_ar': 'زي النيل',
                        'title_en': 'Zy El Nil',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                    {
                        'title_ar': 'العقدة اتفكت',
                        'title_en': 'El Aqda Eftakat',
                        'lyricists': [('صابر كمال', 'Saber Kamal')],
                        'composers': [('شريف بدر', 'Sherif Badr')],
                        'arrangers': [('خالد عصمت', 'Khaled Esmat'), ('عمرو اسماعيل', 'Amro Ismail')],
                    },
                    {
                        'title_ar': 'نرجع تاني',
                        'title_en': 'Nargaa Tani',
                        'lyricists': [('السيد علي', 'El Sayed Ali')],
                        'composers': [('أحمد يوسف', 'Ahmed Youssef')],
                        'arrangers': [('محمد شفيق', 'Mohamed Shafik')],
                    },
                    {
                        'title_ar': 'Welcome To The Life',
                        'title_en': 'Welcome To The Life',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('brain haze', 'Brain Haze')],
                        'featured_artists': [('Akon', 'Akon')],
                    },
                    {
                        'title_ar': 'اطمني',
                        'title_en': 'Atmeni',
                        'lyricists': [('هشام صادق', 'Hisham Sadek')],
                        'composers': [('شريف بدر', 'Sherif Badr')],
                        'arrangers': [('أحمد عبد السلام', 'Ahmed Abdel Salam')],
                    },
                    {
                        'title_ar': 'في الحياة',
                        'title_en': 'Fi El Hayat',
                        'lyricists': [('احمد علي موسى', 'Ahmed Ali Moussa')],
                        'composers': [('محمد عبيه', 'Mohamed Abeih')],
                        'arrangers': [('أحمد إبراهيم', 'Ahmed Ibrahim')],
                    },
                    {
                        'title_ar': 'ماتتغيري بقا',
                        'title_en': 'Mattaghayri Baqa',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('علي شعبان', 'Ali Shaban')],
                        'arrangers': [('كريم عبد الوهاب', 'Karim Abdel Wahab')],
                    },
                    {
                        'title_ar': 'كل اللهجات',
                        'title_en': 'Kol El Lahgat',
                        'lyricists': [('سيد علي', 'Sayed Ali'), ('تامر حسني', 'Tamer Hosny')],
                        'composers': [('احمد يوسف', 'Ahmed Youssef')],
                        'arrangers': [('عبد الرحمن شوقي', 'Abdel Rahman Shokry'), ('خالد عصمت', 'Khaled Esmat')],
                    },
                ],
            },
            'Smile': {
                'year': 2012,
                'songs': [
                    {
                        'title_ar': 'Smile',
                        'title_en': 'Smile',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('طارق فريتخ', 'Tarek Fritkh')],
                        'featured_artists': [('شاغي', 'Shaggy')],
                    },
                ],
            },
            'اللى جاى احلى': {
                'year': 2011,
                'songs': [
                    {
                        'title_ar': 'اللي جاي احلى',
                        'title_en': 'Elly Gay Ahla',
                        'lyricists': [('تامر حسني', 'Tamer Hosny'), ('وليد الغزالي', 'Walid El Ghazaly')],
                        'composers': [('تامر حسني', 'Tamer Hosny'), ('كريم محسن', 'Karim Mohsen')],
                        'arrangers': [('كريم عبد الوهاب', 'Karim Abdel Wahab')],
                    },
                    {
                        'title_ar': 'عرفت تغير من نفسها',
                        'title_en': 'Arafat Taghar Men Nafsha',
                        'lyricists': [('محمد نصار', 'Mohamed Nassar')],
                        'composers': [('كريم محسن', 'Karim Mohsen')],
                        'arrangers': [('كريم عبد الوهاب', 'Karim Abdel Wahab')],
                    },
                    {
                        'title_ar': 'أكلمها',
                        'title_en': 'Aklemha',
                        'lyricists': [('بهاء الدين محمد', 'Bahaa El Din Mohamed')],
                        'composers': [('محمد رحيم', 'Mohamed Rahim')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'دايما معاك',
                        'title_en': 'Dayma Maak',
                        'lyricists': [('عبير الرزاز', 'Abeer El Razzaz')],
                        'composers': [('علي شعبان', 'Ali Shaban')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'اللي عدا عدا',
                        'title_en': 'Elly Ada Ada',
                        'lyricists': [('محمد مصطفى', 'Mohamed Mostafa')],
                        'composers': [('عبد الرحمن شوقي', 'Abdel Rahman Shokry')],
                        'arrangers': [('كريم اسامة', 'Karim Osama')],
                    },
                    {
                        'title_ar': 'مايهونش عليا',
                        'title_en': 'Mahyonesh Aleya',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('محمد النادي', 'Mohamed El Nadi')],
                        'arrangers': [('كريم أسامة', 'Karim Osama')],
                    },
                    {
                        'title_ar': 'كمل لوحدك',
                        'title_en': 'Kaml Lewahdak',
                        'lyricists': [('محمد مصطفى', 'Mohamed Mostafa')],
                        'composers': [('أحمد محيي', 'Ahmed Mohy')],
                        'arrangers': [('مدحت خميس', 'Madhat Khames')],
                    },
                    {
                        'title_ar': 'ماتسألنيش',
                        'title_en': 'Matasalnish',
                        'lyricists': [('امير طعيمة', 'Amer Taaema')],
                        'composers': [('محمد النادي', 'Mohamed El Nadi')],
                        'arrangers': [('محمد شفيق', 'Mohamed Shafik')],
                        'featured_artists': [('بسمة بوسيل', 'Basma Boussel')],
                    },
                    {
                        'title_ar': 'أجمل هدية',
                        'title_en': 'Ajmel Hadiya',
                        'lyricists': [('أمير طعيمة', 'Amer Taaema')],
                        'composers': [('تامر علي', 'Tamer Ali')],
                        'arrangers': [('احمد ابراهيم', 'Ahmed Ibrahim')],
                        'featured_artists': [('ياسر رشدي', 'Yasser Rashdi')],
                    },
                    {
                        'title_ar': 'إرتاح',
                        'title_en': 'Ertaah',
                        'lyricists': [('احمد المالكي', 'Ahmed El Malki')],
                        'composers': [('محمد وزيري', 'Mohamed Waziri')],
                        'arrangers': [('محمد الشاعر', 'Mohamed El Shaer')],
                    },
                    {
                        'title_ar': 'ساعدني أنساك',
                        'title_en': 'Saedni Ansak',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('نور', 'Nour')],
                    },
                    {
                        'title_ar': 'كل يوم أحبه تاني',
                        'title_en': 'Kol Youm Ahobbo Tani',
                        'lyricists': [('عبير الرزاز', 'Abeer El Razzaz')],
                        'composers': [('تامر حسني', 'Tamer Hosny'), ('علي شعبان', 'Ali Shaban')],
                        'arrangers': [('كريم عبد الوهاب', 'Karim Abdel Wahab')],
                    },
                    {
                        'title_ar': 'ولا تسوى',
                        'title_en': 'Wla Tasy',
                        'lyricists': [('تامر حسني', 'Tamer Hosny'), ('عبد الرحمن شوقي', 'Abdel Rahman Shokry')],
                        'composers': [('عبد الرحمن شوقي', 'Abdel Rahman Shokry')],
                        'arrangers': [('فادي بدر', 'Fadi Badr')],
                    },
                    {
                        'title_ar': 'أنا مصري',
                        'title_en': 'Ana Masry',
                        'lyricists': [('تييام', 'Tiyam')],
                        'composers': [('علي شعبان', 'Ali Shaban')],
                        'arrangers': [('يحيى نور', 'Yahya Nour')],
                    },
                ],
            },
            'اخترت صح': {
                'year': 2010,
                'songs': [
                    {
                        'title_ar': 'لو هكون غير ليك',
                        'title_en': 'Law Hakon Ghayr Lek',
                        'lyricists': [('وليد الغزالي', 'Walid El Ghazaly')],
                        'composers': [('كريم محسن', 'Karim Mohsen')],
                        'arrangers': [('كريم عبد الوهاب', 'Karim Abdel Wahab')],
                    },
                    {
                        'title_ar': 'عين شمس',
                        'title_en': 'Ain Shams',
                        'lyricists': [('محمد جمعه', 'Mohamed Gomaa')],
                        'composers': [('محمد رحيم', 'Mohamed Rahim')],
                        'arrangers': [('أمير محروس', 'Amir Mahrous')],
                    },
                    {
                        'title_ar': 'صحيت علي صوتها',
                        'title_en': 'Sahet Ala Sotoha',
                        'lyricists': [('أمير طعيمة', 'Amer Taaema')],
                        'composers': [('عزيز الشافعي', 'Aziz El Shafei')],
                        'arrangers': [('وسام عبد المنعم', 'Wessam Abdel Monem')],
                    },
                    {
                        'title_ar': 'إطمن',
                        'title_en': 'Etmen',
                        'lyricists': [('تامر حسني', 'Tamer Hosny'), ('محمد رحيم', 'Mohamed Rahim')],
                        'composers': [('تامر حسني', 'Tamer Hosny'), ('محمد رحيم', 'Mohamed Rahim')],
                        'arrangers': [('تميم', 'Tamim')],
                        'featured_artists': [('علياء حسني', 'Aliaa Hosny')],
                    },
                    {
                        'title_ar': 'لأول مره',
                        'title_en': 'La Awel Marra',
                        'lyricists': [('شيماء الشربيني', 'Shaimaa El Sharbini')],
                        'composers': [('تامر حسني', 'Tamer Hosny'), ('كريم محسن', 'Karim Mohsen')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                    {
                        'title_ar': 'يا سلام Sweet Melody',
                        'title_en': 'Ya Salam Sweet Melody',
                        'lyricists': [('أحمد جادو', 'Ahmed Gado')],
                        'composers': [('كريم محسن', 'Karim Mohsen'), ('أحمد يوسف', 'Ahmed Youssef')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'قفلت قلبي',
                        'title_en': 'Qaflt Albi',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('محمد الصاوي', 'Mohamed El Sawy')],
                        'arrangers': [('محمد زقزوق', 'Mohamed Zakzouk')],
                    },
                    {
                        'title_ar': 'يانا يامفيش',
                        'title_en': 'Yana Ya Mafish',
                        'lyricists': [('أمير طعيمة', 'Amer Taaema')],
                        'composers': [('محمد النادي', 'Mohamed El Nadi')],
                        'arrangers': [('محمد شفيق', 'Mohamed Shafik'), ('كريم اسامه', 'Karim Osama')],
                    },
                    {
                        'title_ar': 'مستني اليوم',
                        'title_en': 'Mostani El Youm',
                        'lyricists': [('وليد الغزالي', 'Walid El Ghazaly')],
                        'composers': [('كريم محسن', 'Karim Mohsen')],
                        'arrangers': [('كريم عبد الوهاب', 'Karim Abdel Wahab')],
                    },
                    {
                        'title_ar': 'يا واحشني',
                        'title_en': 'Ya Waheshni',
                        'lyricists': [('تـيام', 'Tiyam')],
                        'composers': [('علي شعبان', 'Ali Shaban')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'بتصعب عليا نفسي',
                        'title_en': 'Betsaab Aleya Nafsi',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('نور', 'Nour')],
                    },
                    {
                        'title_ar': 'كام واحد فينا',
                        'title_en': 'Kam Wahed Feena',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('مدحت خميس', 'Madhat Khames')],
                    },
                    {
                        'title_ar': 'تعرفي',
                        'title_en': 'Taarifi',
                        'lyricists': [('محمد عبد الجابر', 'Mohamed Abdel Gaber')],
                        'composers': [('محمد رحيم', 'Mohamed Rahim')],
                        'arrangers': [('عصمت وجيه', 'Esmat Wagih')],
                    },
                    {
                        'title_ar': 'إخترت صح',
                        'title_en': 'Ekhtart Sah',
                        'lyricists': [('بهاء الدين محمد', 'Bahaa El Din Mohamed')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                ],
            },
            'هاعيش حياتى': {
                'year': 2009,
                'songs': [
                    {
                        'title_ar': 'كل اللي فات',
                        'title_en': 'Kol Elly Fat',
                        'lyricists': [('عبير الرزاز', 'Abeer El Razzaz'), ('تامر حسني', 'Tamer Hosny')],
                        'composers': [('كريم محسن', 'Karim Mohsen')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'تاعبة كل الناس',
                        'title_en': 'Taaba Kol El Nas',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('كريم محسن', 'Karim Mohsen')],
                        'arrangers': [('نور', 'Nour')],
                    },
                    {
                        'title_ar': 'يا حبيبي شوف',
                        'title_en': 'Ya Habibi Shof',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('كريم عبد الوهاب', 'Karim Abdel Wahab')],
                    },
                    {
                        'title_ar': 'هاعيش حياتي',
                        'title_en': 'Haaysh Hayaty',
                        'lyricists': [('وليد الغزالي', 'Walid El Ghazaly')],
                        'composers': [('كريم محسن', 'Karim Mohsen')],
                        'arrangers': [('كريم عبد الوهاب', 'Karim Abdel Wahab')],
                    },
                    {
                        'title_ar': 'وأحلم ليه',
                        'title_en': 'Wa Ahlam Leih',
                        'lyricists': [('تيام', 'Tiyam'), ('عصام حسني', 'Essam Hosny')],
                        'composers': [('علي شعبان', 'Ali Shaban')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'بغير عليها',
                        'title_en': 'Baghir Aleiha',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('أحمد إبراهيم', 'Ahmed Ibrahim')],
                    },
                    {
                        'title_ar': 'أنت مشيت',
                        'title_en': 'Enta Mashiet',
                        'lyricists': [('عبد العزيز عمار', 'Abdel Aziz Amar'), ('تامر حسني', 'Tamer Hosny')],
                        'composers': [('حسام البجيرمي', 'Hossam El Bogrimi')],
                        'arrangers': [('أسامة عبد الهادي', 'Osama Abdel Hadi')],
                    },
                    {
                        'title_ar': 'حاجات كتير',
                        'title_en': 'Hagat Kteer',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('نور', 'Nour')],
                    },
                    {
                        'title_ar': 'خنتك إمبارح',
                        'title_en': 'Khantak Embareh',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'حياتي فداك',
                        'title_en': 'Hayaty Fadak',
                        'lyricists': [('محمد نصار', 'Mohamed Nassar')],
                        'composers': [('كريم محسن', 'Karim Mohsen')],
                        'arrangers': [('كريم عبد الوهاب', 'Karim Abdel Wahab')],
                    },
                    {
                        'title_ar': 'رسمي.. فهمي.. نظمي',
                        'title_en': 'Rasmy Fahmy Nazmi',
                        'lyricists': [('محمد رحيم', 'Mohamed Rahim')],
                        'composers': [('محمد رحيم', 'Mohamed Rahim')],
                        'arrangers': [('كريم عبد الوهاب', 'Karim Abdel Wahab')],
                    },
                    {
                        'title_ar': 'تعالي ارجع تاني',
                        'title_en': 'Taali Argaa Tani',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'بينك وبيني',
                        'title_en': 'Beinak Wa Beini',
                        'lyricists': [('محمد جمعة', 'Mohamed Gomaa')],
                        'composers': [('محمد رحيم', 'Mohamed Rahim')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'هو فين',
                        'title_en': 'Howa Fein',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'Come Back To Me',
                        'title_en': 'Come Back To Me',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('كريم عبد الوهاب', 'Karim Abdel Wahab')],
                    },
                ],
            },
            'قرب كمان': {
                'year': 2008,
                'songs': [
                    {
                        'title_ar': 'دايب',
                        'title_en': 'Dayeb',
                        'lyricists': [('محمد عاطف', 'Mohamed Atef')],
                        'composers': [('رامي جمال', 'Ramy Gamal')],
                        'arrangers': [('نور', 'Nour')],
                    },
                    {
                        'title_ar': 'ماتوصنيش',
                        'title_en': 'Matwanesish',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'بكلمة نتصالح',
                        'title_en': 'Bekalma Netasalh',
                        'lyricists': [('عبير الرزاز', 'Abeer El Razzaz')],
                        'composers': [('علي شعبان', 'Ali Shaban')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'قرب كمان',
                        'title_en': 'Orab Kaman',
                        'lyricists': [('عبير الرزاز', 'Abeer El Razzaz')],
                        'composers': [('علي شعبان', 'Ali Shaban')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'اسكتي',
                        'title_en': 'Esketi',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'افتكرلي',
                        'title_en': 'Eftakarli',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'يا تاعبني',
                        'title_en': 'Ya Taabni',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('توما', 'Toma')],
                    },
                    {
                        'title_ar': 'قلبي اللي حبك',
                        'title_en': 'Albi Elly Habbak',
                        'lyricists': [('نصر محروس', 'Nassr Mahrous'), ('تامر حسني', 'Tamer Hosny')],
                        'composers': [('محمد يحيى', 'Mohamed Yehia')],
                        'arrangers': [('توما', 'Toma')],
                    },
                    {
                        'title_ar': 'قسمة ونصيب',
                        'title_en': 'Qasma Wenaseeb',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'بعيد عن عيني',
                        'title_en': 'Baeed An Aini',
                        'lyricists': [('عبد العزيز الشافعي', 'Abdel Aziz El Shafei')],
                        'composers': [('عبد العزيز الشافعي', 'Abdel Aziz El Shafei')],
                        'arrangers': [('نور', 'Nour')],
                    },
                    {
                        'title_ar': 'هي دي',
                        'title_en': 'Hi Di',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny'), ('وحسام البجيرمي', 'Hossam El Bogrimi')],
                        'arrangers': [('محمد زقزوق', 'Mohamed Zakzouk')],
                    },
                    {
                        'title_ar': 'أيام زمان',
                        'title_en': 'Ayam Zaman',
                        'lyricists': [('جمال الخولي', 'Gamal El Khouly')],
                        'composers': [('محمد يحيى', 'Mohamed Yehia')],
                        'arrangers': [('أحمد إبراهيم', 'Ahmed Ibrahim')],
                    },
                    {
                        'title_ar': 'روح قلبي',
                        'title_en': 'Roh Albi',
                        'lyricists': [('نصر محروس', 'Nassr Mahrous'), ('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('أمير محروس', 'Amir Mahrous')],
                    },
                    {
                        'title_ar': 'أصعب إحساس',
                        'title_en': 'Asaab Ehsas',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('خالد نبيل', 'Khaled Nabil')],
                    },
                ],
            },
            'الجنه فى بيوتنا': {
                'year': 2007,
                'songs': [
                    {
                        'title_ar': 'شهر رمضان',
                        'title_en': 'Shahr Ramadan',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                    {
                        'title_ar': 'صاحبني يا أبويا',
                        'title_en': 'Sahbeni Ya Abuya',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                    {
                        'title_ar': 'تيجي ننسي',
                        'title_en': 'Teiji Nensi',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                    {
                        'title_ar': 'يا أرحم الراحمين',
                        'title_en': 'Ya Arham El Rahimeen',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                    {
                        'title_ar': 'لو عايز الخير',
                        'title_en': 'Law Ayez El Kheir',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                    {
                        'title_ar': 'الجنة في بيوتنا',
                        'title_en': 'El Ganna Fi Beyotna',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                    {
                        'title_ar': 'ونجحنا السنة دي',
                        'title_en': 'Wenahna El Senna Di',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                    {
                        'title_ar': 'يا رب أنا تعبان',
                        'title_en': 'Ya Rab Ana Taaban',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                    {
                        'title_ar': 'وعينيها دمعت',
                        'title_en': 'Wa Eneiha Damat',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                    {
                        'title_ar': 'أنا مش عارف أتغير',
                        'title_en': 'Ana Mesh Aref Atagayar',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'سبحان الله',
                        'title_en': 'Subhan Allah',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'أسماء الله الحسني',
                        'title_en': 'Asmaa Allah El Hosna',
                        'lyricists': [],
                        'composers': [('سيد مكاوي', 'Sayed Makawi')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                    {
                        'title_ar': 'ديني ودينك',
                        'title_en': 'Dini Wa Denak',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('جلال فهمي', 'Galal Fahmy')],
                    },
                ],
            },
            'يا بنت الإيه': {
                'year': 2007,
                'songs': [
                    {
                        'title_ar': 'يا بنت الإيه',
                        'title_en': 'Ya Bent El Eih',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('أمير محروس', 'Amir Mahrous')],
                    },
                    {
                        'title_ar': 'ماكنتش مبين',
                        'title_en': 'Makontsh Bayen',
                        'lyricists': [('هاني علي', 'Hany Ali')],
                        'composers': [('تامر علي', 'Tamer Ali')],
                        'arrangers': [('محمد مصطفي', 'Mohamed Mostafa')],
                    },
                    {
                        'title_ar': 'عرفت اللي فيها',
                        'title_en': 'Araf Elly Fiha',
                        'lyricists': [('نادر عبدالله', 'Nader Abdallah')],
                        'composers': [('تامر علي', 'Tamer Ali')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'انت واحشني',
                        'title_en': 'Enta Waheshni',
                        'lyricists': [('خالد أمين', 'Khaled Amin')],
                        'composers': [('محمد رحيم', 'Mohamed Rahim')],
                        'arrangers': [('أمير محروس', 'Amir Mahrous'), ('طارق حسيب', 'Tarek Haseeb')],
                    },
                    {
                        'title_ar': 'اعتذري',
                        'title_en': 'Etazari',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('هيثم شاكر', 'Hitham Shaker')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'سيب الحب',
                        'title_en': 'Seb El Hob',
                        'lyricists': [('أمير طعيمة', 'Amer Taaema')],
                        'composers': [('خالد عز', 'Khaled Ezz')],
                        'arrangers': [('توما', 'Toma')],
                    },
                    {
                        'title_ar': 'ارجعلي',
                        'title_en': 'Argeli',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'حاسس بخوف',
                        'title_en': 'Hass Be Khof',
                        'lyricists': [('محمد حامد', 'Mohamed Hamed')],
                        'composers': [('تامر علي', 'Tamer Ali')],
                        'arrangers': [('أحمد ابراهيم', 'Ahmed Ibrahim')],
                    },
                    {
                        'title_ar': 'محدش حاسس بيا',
                        'title_en': 'Mahdash Hass Biya',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                    {
                        'title_ar': 'كل سنة وانت طيب',
                        'title_en': 'Kol Senna Wa Enta Tayeb',
                        'lyricists': [('نصر محروس', 'Nassr Mahrous')],
                        'composers': [('وليد سعد', 'Walid Saad')],
                        'arrangers': [('أمير محروس', 'Amir Mahrous')],
                    },
                    {
                        'title_ar': 'صوتك',
                        'title_en': 'Sawtak',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('أحمد عادل', 'Ahmed Adel')],
                    },
                    {
                        'title_ar': 'الله يباركلي فيك',
                        'title_en': 'Allah Ybarakli Fik',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('أحمد عادل', 'Ahmed Adel')],
                    },
                    {
                        'title_ar': 'أنا ولا عارف',
                        'title_en': 'Ana Wla Aref',
                        'lyricists': [('تامر حسني', 'Tamer Hosny')],
                        'composers': [('تامر حسني', 'Tamer Hosny')],
                        'arrangers': [('تميم', 'Tamim')],
                    },
                ],
            },
        }

        created_songs = 0
        created_persons = 0
        created_credits = 0
        skipped_albums = 0

        for album_title, album_data in albums_data.items():
            album = Album.objects.filter(title_ar=album_title).first()
            if not album:
                self.stdout.write(self.style.WARNING(f'Album not found: {album_title}'))
                skipped_albums += 1
                continue

            self.stdout.write(f'Processing album: {album_title}')

            for song_data in album_data['songs']:
                # Get or create recording studio based on arranger
                recording_studio = None
                arrangers = song_data.get('arrangers', [])
                if arrangers:
                    # Map arrangers to studios
                    arranger_to_studio = {
                        'عادل حقي': 'استوديو عادل حقي',
                        'النابلسي': 'استوديو النابلسي',
                        'Kay Music': 'استوديو كاي ميوزيك',
                        'كوليبكس': 'استوديو كوليبكس',
                        'أحمد عادل': 'استوديو أحمد عادل',
                        'خالد نبيل': 'استوديو خالد نبيل',
                        'جلال فهمي': 'استوديو جلال فهمي',
                        'جلال حمداوي': 'استوديو جلال حمداوي',
                        'أحمد عبد السلام': 'استوديو أحمد عبد السلام',
                        'وسام محمد': 'استوديو وسام محمد',
                        'شريف مكاوي': 'استوديو شريف مكاوي',
                        'علي فتح الله': 'استوديو علي فتح الله',
                        'محمد ياسر': 'استوديو محمد ياسر',
                        'تميم': 'استوديو تميم',
                        'إلهامي دهيمة': 'استوديو إلهامي دهيمة',
                        'أحمد حسام': 'استوديو إلهامي دهيمة',
                        'حسام الصعبي': 'استوديو حسام الصعبي',
                        'يحيى يوسف': 'استوديو يحيى يوسف',
                    }
                    
                    for arranger_ar, _ in arrangers:
                        if arranger_ar in arranger_to_studio:
                            from backend.studios_app.models import Studio
                            studio_name = arranger_to_studio[arranger_ar]
                            recording_studio = Studio.objects.filter(name=studio_name).first()
                            if recording_studio:
                                break

                # Use default studio if none found
                if not recording_studio:
                    from backend.studios_app.models import Studio
                    recording_studio = Studio.objects.filter(name='استوديو ساوند باور').first()

                song, created = Song.objects.get_or_create(
                    title_ar=song_data['title_ar'],
                    defaults={
                        'title_en': song_data.get('title_en', ''),
                        'release_year': album_data['year'],
                        'song_type': Song.SongType.ALBUM_TRACK,
                        'album': album,
                        'genre': song_data.get('genre', Song.Genre.EGYPTIAN_POP),
                        'mood': song_data.get('mood', Song.Mood.ROMANTIC),
                        'duration_seconds': song_data.get('duration_seconds', 240),
                        'recording_studio': recording_studio,
                    }
                )
                if created:
                    created_songs += 1
                    self.stdout.write(f'  Created song: {song_data["title_ar"]}')
                else:
                    # Update existing song with missing fields
                    updated = False
                    if not song.genre:
                        song.genre = song_data.get('genre', Song.Genre.EGYPTIAN_POP)
                        updated = True
                    if not song.mood:
                        song.mood = song_data.get('mood', Song.Mood.ROMANTIC)
                        updated = True
                    if not song.duration_seconds:
                        song.duration_seconds = song_data.get('duration_seconds', 240)
                        updated = True
                    if not song.recording_studio and recording_studio:
                        song.recording_studio = recording_studio
                        updated = True
                    if updated:
                        song.save()
                        self.stdout.write(f'  Updated song: {song_data["title_ar"]}')

                # Add Tamer Hosny as singer
                SongCredit.objects.get_or_create(
                    song=song,
                    person=tamer_hosny,
                    role=SongCredit.Role.SINGER,
                )
                created_credits += 1

                # Add featured artists
                for name_ar, name_en in song_data.get('featured_artists', []):
                    person = self._get_or_create_person(name_ar, name_en, Person.Role.SINGER)
                    if person:
                        SongCredit.objects.get_or_create(
                            song=song,
                            person=person,
                            role=SongCredit.Role.FEATURED_ARTIST,
                        )
                        created_credits += 1

                # Add lyricists
                for name_ar, name_en in song_data.get('lyricists', []):
                    person = self._get_or_create_person(name_ar, name_en, Person.Role.POET)
                    if person:
                        SongCredit.objects.get_or_create(
                            song=song,
                            person=person,
                            role=SongCredit.Role.LYRICIST,
                        )
                        created_credits += 1

                # Add composers
                for name_ar, name_en in song_data.get('composers', []):
                    person = self._get_or_create_person(name_ar, name_en, Person.Role.COMPOSER)
                    if person:
                        SongCredit.objects.get_or_create(
                            song=song,
                            person=person,
                            role=SongCredit.Role.COMPOSER,
                        )
                        created_credits += 1

                # Add arrangers
                for name_ar, name_en in song_data.get('arrangers', []):
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
                f'Successfully created {created_songs} songs, {created_persons} persons, and {created_credits} credits. '
                f'Skipped {skipped_albums} albums not found in database.'
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
            self.stdout.write(f'    Created person: {name_ar}')
            return person
        return person
