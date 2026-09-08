from django.core.management.base import BaseCommand

from backend.main_app.shared_utils.song_recommendations import refresh_all


class Command(BaseCommand):
    help = "Recomputes SongSimilarity and UserSongRecommendation from current listening data."

    def handle(self, *args, **options):
        similarity_count, recommendation_count = refresh_all()
        self.stdout.write(self.style.SUCCESS(
            f'Wrote {similarity_count} SongSimilarity rows and {recommendation_count} UserSongRecommendation rows.'
        ))
