import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings")

app = Celery("backend")

# Читаем конфиг из Django settings, все переменные CELERY_*
app.config_from_object("django.conf:settings", namespace="CELERY")

# Авто‑обнаружение tasks.py во всех приложениях
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Debug task: Request: {self.request!r}")
