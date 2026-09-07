"""Site-wide points/streak/badges - one small shared system that every
feature (the daily guess game, likes, duets, remixes...) feeds into,
instead of each feature keeping its own separate score. A leaderboard
and a profile's badge shelf only make sense if all activity funnels
into the same UserGameProfile.
"""
from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend.main_app.models import UserGameProfile


def get_or_create_profile(user):
    profile, _created = UserGameProfile.objects.get_or_create(user=user)
    return profile


def record_daily_activity(profile):
    """Bumps the login-streak at most once per calendar day - a
    yesterday-to-today gap continues it, any bigger gap resets it to 1.
    """
    today = timezone.localdate()
    if profile.last_active_date == today:
        return
    if profile.last_active_date == today - timedelta(days=1):
        profile.current_streak += 1
    else:
        profile.current_streak = 1
    profile.longest_streak = max(profile.longest_streak, profile.current_streak)
    profile.last_active_date = today
    profile.save(update_fields=['current_streak', 'longest_streak', 'last_active_date'])


def award_points(user, amount):
    """Every point-worthy action goes through here - it's also what
    counts as "being active today" for the streak, even actions (like a
    losing guess) that award 0 points still keep the streak alive.
    """
    profile = get_or_create_profile(user)
    record_daily_activity(profile)
    if amount:
        profile.points += amount
        profile.save(update_fields=['points'])
    return profile


# Points for the lighter-weight activities - the daily guess game has
# its own listening-based formula (see website_app.views), since how
# well you played it is worth reflecting in the score.
POINTS_LIKE = 2
POINTS_DUET_COMPLETED = 20
POINTS_GUESS_LOSS = 5


BADGES = [
    {'key': 'first_steps', 'metric': 'points', 'threshold': 1, 'icon': 'bi-flag-fill', 'label': _('أول خطوة')},
    {'key': 'bronze', 'metric': 'points', 'threshold': 100, 'icon': 'bi-award', 'label': _('عضو نشيط')},
    {'key': 'silver', 'metric': 'points', 'threshold': 500, 'icon': 'bi-award-fill', 'label': _('عضو متميز')},
    {'key': 'gold', 'metric': 'points', 'threshold': 2000, 'icon': 'bi-trophy', 'label': _('نجم الموقع')},
    {'key': 'legend', 'metric': 'points', 'threshold': 5000, 'icon': 'bi-trophy-fill', 'label': _('أسطورة تامر')},
    {'key': 'streak_3', 'metric': 'streak', 'threshold': 3, 'icon': 'bi-fire', 'label': _('3 أيام متتالية')},
    {'key': 'streak_7', 'metric': 'streak', 'threshold': 7, 'icon': 'bi-fire', 'label': _('أسبوع كامل')},
    {'key': 'streak_30', 'metric': 'streak', 'threshold': 30, 'icon': 'bi-fire', 'label': _('شهر كامل بدون انقطاع')},
]


def unlocked_badges(profile):
    unlocked = []
    for badge in BADGES:
        value = profile.points if badge['metric'] == 'points' else profile.longest_streak
        if value >= badge['threshold']:
            unlocked.append(badge)
    return unlocked
