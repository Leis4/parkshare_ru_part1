FROM python:3.11-bullseye

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Системные зависимости для Postgres, GDAL/GEOS (на будущее) и компиляции
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    binutils \
    libproj-dev \
    libgeos-dev \
    libspatialindex-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Настройки GDAL/PROJ (если когда-нибудь добавишь GeoDjango)
ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so
ENV PROJ_LIB=/usr/share/proj

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем проект
COPY . /app/

# Каталоги для статики и медиа
RUN mkdir -p /app/staticfiles /app/media

EXPOSE 8000

# По умолчанию — gunicorn, но в docker-compose мы переопределим команду
CMD ["gunicorn", "backend.config.wsgi:application", "--bind", "0.0.0.0:8000"]
