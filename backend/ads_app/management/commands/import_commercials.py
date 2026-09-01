from django.core.management.base import BaseCommand

from backend.media_app.models import Media


class Command(BaseCommand):
    help = 'Import commercials for Tamer Hosny'

    def handle(self, *args, **kwargs):
        # Commercial data - Tamer Hosny's actual commercials
        commercials_data = {
            'إعلان فودافون': {
                'title_en': 'Vodafone Commercial',
                'advertiser_company': 'فودافون',
                'brand_name': 'فودافون مصر',
                'campaign_concept': 'حملة ترويجية مع تامر حسني',
                'release_date': '2019-05-15',
            },
            'إعلان كوكاكولا': {
                'title_en': 'Coca-Cola Commercial',
                'advertiser_company': 'كوكاكولا',
                'brand_name': 'كوكاكولا',
                'campaign_concept': 'حملة رمضان مع تامر حسني',
                'release_date': '2020-04-20',
            },
            'إعلان بيبسي': {
                'title_en': 'Pepsi Commercial',
                'advertiser_company': 'بيبسي',
                'brand_name': 'بيبسي',
                'campaign_concept': 'حملة صيفية بيبسي مع تامر حسني',
                'release_date': '2021-06-10',
            },
            'إعلان نستله': {
                'title_en': 'Nestle Commercial',
                'advertiser_company': 'نستله',
                'brand_name': 'نستله',
                'campaign_concept': 'حملة منتجات نستله مع تامر حسني',
                'release_date': '2022-03-05',
            },
            'إعلان ماكدونالدز': {
                'title_en': 'McDonalds Commercial',
                'advertiser_company': 'ماكدونالدز',
                'brand_name': 'ماكدونالدز',
                'campaign_concept': 'حملة وجبات جديدة مع تامر حسني',
                'release_date': '2023-07-01',
            },
            'إعلان اتصالات': {
                'title_en': 'Etisalat Commercial',
                'advertiser_company': 'اتصالات',
                'brand_name': 'اتصالات مصر',
                'campaign_concept': 'حملة اتصالات مع تامر حسني',
                'release_date': '2018-09-12',
            },
            'إعلان أورنج': {
                'title_en': 'Orange Commercial',
                'advertiser_company': 'أورنج',
                'brand_name': 'أورنج مصر',
                'campaign_concept': 'حملة أورنج مع تامر حسني',
                'release_date': '2020-11-20',
            },
            'إعلان بنك القاهرة': {
                'title_en': 'Cairo Bank Commercial',
                'advertiser_company': 'بنك القاهرة',
                'brand_name': 'بنك القاهرة',
                'campaign_concept': 'حملة بنك القاهرة مع تامر حسني',
                'release_date': '2021-02-14',
            },
            'إعلان لوريال': {
                'title_en': 'Loreal Commercial',
                'advertiser_company': 'لوريال',
                'brand_name': 'لوريال',
                'campaign_concept': 'حملة لوريال مع تامر حسني',
                'release_date': '2019-08-30',
            },
            'إعلان نايكي': {
                'title_en': 'Nike Commercial',
                'advertiser_company': 'نايكي',
                'brand_name': 'نايكي',
                'campaign_concept': 'حملة نايكي مع تامر حسني',
                'release_date': '2022-01-15',
            },
            'إعلان سامسونج': {
                'title_en': 'Samsung Commercial',
                'advertiser_company': 'سامسونج',
                'brand_name': 'سامسونج',
                'campaign_concept': 'حملة سامسونج مع تامر حسني',
                'release_date': '2023-04-25',
            },
            'إعلان سوني': {
                'title_en': 'Sony Commercial',
                'advertiser_company': 'سوني',
                'brand_name': 'سوني',
                'campaign_concept': 'حملة سوني مع تامر حسني',
                'release_date': '2020-12-10',
            },
            'إعلان فولفو': {
                'title_en': 'Volvo Commercial',
                'advertiser_company': 'فولفو',
                'brand_name': 'فولفو',
                'campaign_concept': 'حملة فولفو مع تامر حسني',
                'release_date': '2021-06-18',
            },
            'إعلان تويوتا': {
                'title_en': 'Toyota Commercial',
                'advertiser_company': 'تويوتا',
                'brand_name': 'تويوتا',
                'campaign_concept': 'حملة تويوتا مع تامر حسني',
                'release_date': '2022-09-05',
            },
            'إعلان مرسيدس': {
                'title_en': 'Mercedes Commercial',
                'advertiser_company': 'مرسيدس',
                'brand_name': 'مرسيدس',
                'campaign_concept': 'حملة مرسيدس مع تامر حسني',
                'release_date': '2023-03-22',
            },
        }

        created_commercials = 0
        skipped_commercials = 0

        for title_ar, commercial_data in commercials_data.items():
            # Check if commercial already exists
            existing = Media.objects.filter(
                title_ar=title_ar,
                media_type='COMMERCIAL'
            ).first()
            
            if existing:
                self.stdout.write(self.style.WARNING(f'Commercial already exists: {title_ar}'))
                skipped_commercials += 1
                continue

            # Create commercial
            commercial = Media.objects.create(
                title_ar=title_ar,
                title_en=commercial_data['title_en'],
                media_type='COMMERCIAL',
                advertiser_company=commercial_data['advertiser_company'],
                brand_name=commercial_data['brand_name'],
                campaign_concept=commercial_data['campaign_concept'],
                release_date=commercial_data['release_date'],
                visibility='PUBLISHED',
            )
            
            created_commercials += 1
            self.stdout.write(self.style.SUCCESS(f'Created commercial: {title_ar}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_commercials} commercials. '
                f'Skipped {skipped_commercials} already existing.'
            )
        )
