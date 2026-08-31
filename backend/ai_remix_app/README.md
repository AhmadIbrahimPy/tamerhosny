# AI Remix Generator - نموذج الذكاء الاصطناعي لتوليد الريمكسات

## نظرة عامة

هذا التطبيق يوفر نظاماً متكاملاً لتوليد ريمكسات احترافية من الملفات الصوتية باستخدام تقنيات الذكاء الاصطناعي والتعلم العميق.

## المميزات

### 1. معالجة الصوت المتقدمة
- تحليل تلقائي للملفات الصوتية (BPM، المفتاح الموسيقي، الطيف الترددي)
- تغيير السرعة مع الحفاظ على النبرة
- تغيير النبرة والمفتاح الموسيقي
- تطبيق تأثيرات صوتية احترافية (Compressor، Reverb، Delay، Chorus، إلخ)

### 2. الشبكات العصبية
- نموذج VAE لتوليد الصوت
- طبقات الانتباه لدمج المصادر الصوتية
- شبكة نقل النمط الموسيقي
- مولد الريمكس الذكي

### 3. واجهة المستخدم
- رفع الملفات الصوتية بسهولة
- إنشاء مشاريع الريمكس
- التحكم في معاملات الدمج (الصوت، التوقيت، التلاشي)
- توليد الريمكس بالطريقة التقليدية أو العصبية
 تحميل وتشغيل الريمكسات المولدة

## التثبيت

### 1. تثبيت المكتبات المطلوبة

```bash
pip install -r requirements.txt
```

المكتبات المضافة:
- librosa: لمعالجة الصوت وتحليله
- numpy & scipy: للحسابات العلمية
- soundfile: لقراءة وكتابة الملفات الصوتية
- pydub: لمعالجة الصوت
- torch & torchaudio: للتعلم العميق
- pedalboard: للتأثيرات الصوتية الاحترافية

### 2. تشغيل الهجرات

```bash
python manage.py makemigrations ai_remix_app
python manage.py migrate
```

### 3. إنشاء مجلدات الوسائط

```bash
mkdir -p media/ai_remix/sources
mkdir -p media/ai_remix/outputs
```

## الاستخدام

### عبر واجهة الويب

1. انتقل إلى صفحة `/dashboard/ai_remix/`
2. ارفع الملفات الصوتية في تبويب "Audio Sources"
3. أنشئ مشروعاً جديداً في تبويب "Projects"
4. أضف المصادر الصوتية إلى المشروع
5. اضبط إعدادات الريمكس في تبويب "Create Remix"
6. اضغط على "Generate Remix" أو "Neural AI Remix"

### عبر API

#### رفع ملف صوتي

```bash
POST /api/v1/ai-remix/audio-sources/
Content-Type: multipart/form-data

{
    "name": "Drum Loop",
    "audio_file": <file>,
    "source_type": "DRUMS"
}
```

#### إنشاء مشروع

```bash
POST /api/v1/ai-remix/remix-projects/
Content-Type: application/json

{
    "name": "My Remix",
    "description": "A cool remix",
    "target_bpm": 120,
    "target_key": "C maj"
}
```

#### إضافة مصدر للمشروع

```bash
POST /api/v1/ai-remix/remix-projects/{id}/add_source/
Content-Type: application/json

{
    "audio_source_id": 1,
    "volume": 1.0,
    "start_time": 0.0,
    "fade_in": 0.5,
    "fade_out": 0.5,
    "order": 0
}
```

#### توليد الريمكس

```bash
POST /api/v1/ai-remix/remix-projects/{id}/generate_remix/
Content-Type: application/json

{
    "target_bpm": 120,
    "target_key": "C maj",
    "effects": {
        "compressor": true,
        "reverb": true,
        "limiter": true
    },
    "auto_arrange": true,
    "intelligent_mix": true
}
```

#### توليد الريمكس العصبي

```bash
POST /api/v1/ai-remix/remix-projects/{id}/neural_generate/
Content-Type: application/json
```

## البنية التقنية

### النماذج (Models)

- **AudioSource**: تخزين الملفات الصوتية المصدر
- **RemixProject**: إدارة مشاريع الريمكس
- **RemixSource**: ربط المصادر بالمشاريع مع إعدادات الدمج
- **RemixOutput**: تخزين الريمكسات المولدة
- **AIModel**: إدارة نماذج الذكاء الاصطناعي

### معالج الصوت (AudioProcessor)

```python
from backend.ai_remix_app.core.audio_processor import AudioProcessor

processor = AudioProcessor(sample_rate=44100)

# تحميل وتحليل
audio_data, sr = processor.load_audio('file.mp3')
analysis = processor.analyze_audio(audio_data)

# تغيير السرعة
changed = processor.change_tempo(audio_data, original_bpm=100, target_bpm=120)

# تطبيق التأثيرات
effects = {
    'compressor': True,
    'reverb': True,
    'limiter': True
}
processed = processor.apply_effects(audio_data, effects)
```

### النموذج العصبي (NeuralRemixModel)

```python
from backend.ai_remix_app.core.neural_remix_model import NeuralRemixModel

model = NeuralRemixModel(device='cpu')

# توليد ريمكس
sources = [audio1, audio2, audio3, audio4]
remix = model.generate_remix(sources)
```

## التأثيرات الصوتية المتاحة

- **Compressor**: ضغط الصوت لتحسين الديناميكية
- **Reverb**: إضافة صدى للمساحة
- **Delay**: تأثير التأخير
- **Chorus**: تأثير الكورس
- **Phaser**: تأثير الفيزر
- **Highpass/Lowpass**: فلاتر ترددية
- **Limiter**: محدد مستوى الصوت

## خيارات التوليد

### الطريقة التقليدية
- دمج المصادر الصوتية معاً
- تطابق BPM والمفتاح الموسيقي
- تطبيق التأثيرات المختارة
- الترتيب التلقائي للمصادر
- الخلط الذكي للمستويات

### الطريقة العصبية
- استخدام الشبكات العصبية العميقة
- توليد تمثيلات متجهية للصوت
- دمج ذكي باستخدام الانتباه
- نقل النمط الموسيقي

## المتطلبات

- Python 3.8+
- Django 6.1
- PyTorch 2.2+
- 4GB RAM على الأقل
- مساحة تخزين كافية للملفات الصوتية

## ملاحظات الأداء

- معالجة الملفات الكبيرة قد تستغرق وقتاً
- يُنصح باستخدام GPU للنموذج العصبي
- يمكن ضبط جودة الإخراج من خلال bitrate و sample_rate

## التطوير المستقبلي

- إضافة المزيد من النماذج العصبية المدربة مسبقاً
- دعم المزيد من صيغ الملفات الصوتية
- تحسين واجهة المستخدم
- إضافة إمكانية التعلم من الريمكسات الموجودة
- دعم المعالجة في الوقت الفعلي

## الدعم

للدعم والاستفسارات، راجع التوثيق الرسمي للمشروع.
