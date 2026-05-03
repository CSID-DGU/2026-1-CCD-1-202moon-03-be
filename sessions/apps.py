from django.apps import AppConfig

class SessionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sessions"
    label = "tadac_sessions"  # 충돌 방지