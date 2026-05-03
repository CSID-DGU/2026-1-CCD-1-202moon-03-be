# Celery가 Django 시작할 때 자동으로 로드되게 함
from .celery import app as celery_app
__all__ = ("celery_app",)
