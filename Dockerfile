FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

# تثبيت الأدوات الأساسية ومُترجم Rust عشان الحزم اللي بتبني بـ Cargo/Maturin زي sphn
RUN apt-get update && apt-get install -y \
    libpq-dev gcc pkg-config curl build-essential \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && rm -rf /var/lib/apt/lists/*

# إضافة مسار الـ Rust/Cargo لمتغيرات البيئة (PATH)
ENV PATH="/root/.cargo/bin:$PATH"

# تثبيت maturin عشان بناء الـ Rust extensions
RUN pip install --no-cache-dir maturin

# أولاً: تثبيت المكتبات الثقيلة
COPY requirements-heavy.txt .
RUN pip install --no-cache-dir --retries 5 --timeout 300 -r requirements-heavy.txt

# ثانياً: تثبيت مكتبات الباك إند العادية
COPY requirements.txt .
RUN pip install --no-cache-dir --retries 5 --timeout 300 -r requirements.txt

# ثالثاً: نسخ باقي ملفات المشروع
COPY . .

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]