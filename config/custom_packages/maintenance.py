"""Site-wide "under development" gate for the public website.

Every public website route answers with a 503 page that shows a loading
spinner plus a random dhikr, rotating every few seconds. Admin, dashboard,
the JSON API, static and uploaded files stay reachable. Switch it off with
MAINTENANCE_MODE=false in credentials/.env.
"""

import json
import random

from django.conf import settings
from django.http import HttpResponse

ADHKAR = [
    'اللهم أنت ربي لا إله إلا أنت، خلقتني وأنا عبدك، وأنا على عهدك ووعدك ما استطعت، أعوذ بك من شر ما صنعت، أبوء لك بنعمتك عليّ، وأبوء بذنبي فاغفر لي فإنه لا يغفر الذنوب إلا أنت',
    'سبحان الله وبحمده، سبحان الله العظيم',
    'لا إله إلا الله وحده لا شريك له، له الملك وله الحمد وهو على كل شيء قدير',
    'لا حول ولا قوة إلا بالله',
    'أستغفر الله العظيم الذي لا إله إلا هو الحي القيوم وأتوب إليه',
    'اللهم صلّ وسلّم على نبينا محمد',
    'حسبي الله لا إله إلا هو عليه توكلت وهو رب العرش العظيم',
    'يا حي يا قيوم برحمتك أستغيث، أصلح لي شأني كله ولا تكلني إلى نفسي طرفة عين',
    'اللهم إني أسألك العفو والعافية في الدنيا والآخرة',
    'ربنا آتنا في الدنيا حسنة وفي الآخرة حسنة وقنا عذاب النار',
    'رب اشرح لي صدري ويسر لي أمري',
    'لا إله إلا أنت سبحانك إني كنت من الظالمين',
    'اللهم اغفر لي ولوالديّ وللمؤمنين والمؤمنات',
    'بسم الله الذي لا يضر مع اسمه شيء في الأرض ولا في السماء وهو السميع العليم',
    'اللهم لا سهل إلا ما جعلته سهلاً، وأنت تجعل الحزن إذا شئت سهلاً',
    'سبحان الله، والحمد لله، ولا إله إلا الله، والله أكبر',
    'اللهم إني أعوذ بك من الهم والحزن، والعجز والكسل، والبخل والجبن، وضلع الدين وغلبة الرجال',
    'رضيت بالله رباً، وبالإسلام ديناً، وبمحمد صلى الله عليه وسلم نبياً',
    'اللهم اجعل في قلبي نوراً، وفي بصري نوراً، وفي سمعي نوراً',
    'يا مقلب القلوب ثبت قلبي على دينك',
    'اللهم اهدني وسددني',
    'اللهم إني أسألك علماً نافعاً، ورزقاً طيباً، وعملاً متقبلاً',
    'الحمد لله الذي أحيانا بعد ما أماتنا وإليه النشور',
    'ربنا لا تؤاخذنا إن نسينا أو أخطأنا',
    'اللهم رحمتك أرجو فلا تكلني إلى نفسي طرفة عين، وأصلح لي شأني كله لا إله إلا أنت',
    'ربنا ظلمنا أنفسنا وإن لم تغفر لنا وترحمنا لنكونن من الخاسرين',
    'اللهم أعنّي على ذكرك وشكرك وحسن عبادتك',
    'سبحان الله وبحمده عدد خلقه ورضا نفسه وزنة عرشه ومداد كلماته',
    'اللهم اكفني بحلالك عن حرامك، وأغنني بفضلك عمن سواك',
    'ربنا هب لنا من أزواجنا وذرياتنا قرة أعين واجعلنا للمتقين إماماً',
    'اللهم إنك عفو تحب العفو فاعف عني',
    'توكلت على الله، ولا حول ولا قوة إلا بالله',
    'اللهم ارحم موتانا واشفِ مرضانا وبارك لنا في أعمارنا',
    'أعوذ بكلمات الله التامات من شر ما خلق',
    'اللهم إني ظلمت نفسي ظلماً كثيراً، ولا يغفر الذنوب إلا أنت، فاغفر لي مغفرة من عندك وارحمني',
    'الحمد لله حمداً كثيراً طيباً مباركاً فيه',
    'اللهم بارك لنا فيما رزقتنا وقنا عذاب النار',
    'يا رب لك الحمد كما ينبغي لجلال وجهك وعظيم سلطانك',
    'ربّ إني لما أنزلت إليّ من خير فقير',
    'اللهم ثبتنا بالقول الثابت في الحياة الدنيا وفي الآخرة',
    'سبحان الله عدد ما خلق، سبحان الله ملء ما خلق، والحمد لله مثل ذلك',
    'اللهم أصلح لي ديني الذي هو عصمة أمري، ودنياي التي فيها معاشي',
    'ربنا تقبل منا إنك أنت السميع العليم',
    'اللهم اجعلنا من التوابين واجعلنا من المتطهرين',
    'إنا لله وإنا إليه راجعون، اللهم أجرني في مصيبتي واخلف لي خيراً منها',
    'اللهم إني أسألك الجنة وما قرب إليها من قول أو عمل',
    'ألا بذكر الله تطمئن القلوب',
]

# First path segments that are never gated (versioned API prefixes are
# matched separately below since they look like /<version>/<app>/...).
_EXEMPT_PREFIXES = ('/i18n/', '/static/', '/uploads/')
_API_APPS = {'main', 'people', 'studios', 'music', 'media', 'concerts', 'ads', 'analytics', 'ai-remix'}

_PAGE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>الموقع قيد التطوير</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 28px; padding: 24px;
    background: radial-gradient(circle at 50% 30%, #1b2a2a, #0b0f10 70%);
    color: #eef3f1; font-family: "Noto Naskh Arabic", "Amiri", "Geeza Pro", "Traditional Arabic", serif;
    text-align: center;
  }
  .spinner {
    width: 54px; height: 54px; border-radius: 50%;
    border: 4px solid rgba(255,255,255,.12); border-top-color: #d6b45a;
    animation: spin 1s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  h1 { margin: 0; font-size: 1.15rem; font-weight: 400; color: #aab7b3; }
  #dhikr {
    max-width: 720px; min-height: 8em; display: flex; align-items: center; justify-content: center;
    font-size: clamp(1.4rem, 4.5vw, 2.1rem); line-height: 2; color: #f3e3b0;
    transition: opacity .7s ease;
  }
  #dhikr.hide { opacity: 0; }
</style>
</head>
<body>
  <div class="spinner" aria-hidden="true"></div>
  <h1>الموقع قيد التطوير… جارٍ التحميل</h1>
  <p id="dhikr">__FIRST__</p>
<script>
  (function () {
    var list = __LIST__, el = document.getElementById('dhikr'), last = el.textContent;
    setInterval(function () {
      var next;
      do { next = list[Math.floor(Math.random() * list.length)]; } while (next === last && list.length > 1);
      last = next;
      el.classList.add('hide');
      setTimeout(function () { el.textContent = next; el.classList.remove('hide'); }, 700);
    }, 7000);
  })();
</script>
</body>
</html>
"""


def _is_exempt(path):
    if path.startswith(_EXEMPT_PREFIXES):
        return True
    admin = f'/{settings.ADMIN_URL_PATH}/'
    dash = f'/{settings.DASHBOARD_URL_PATH}/'
    if path.startswith((admin, dash)):
        return True
    parts = path.split('/')
    return len(parts) > 2 and parts[2] in _API_APPS


class MaintenanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'MAINTENANCE_MODE', False) or _is_exempt(request.path):
            return self.get_response(request)
        # ensure_ascii=False keeps Arabic readable; escape "</" so the list can't close the script tag.
        data = json.dumps(ADHKAR, ensure_ascii=False).replace('</', '<\\/')
        html = _PAGE.replace('__LIST__', data).replace('__FIRST__', random.choice(ADHKAR))
        response = HttpResponse(html, status=503, content_type='text/html; charset=utf-8')
        response['Retry-After'] = '3600'
        response['Cache-Control'] = 'no-store'
        return response
