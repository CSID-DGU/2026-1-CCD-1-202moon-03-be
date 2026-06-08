from django.contrib import admin
from .models import LearningResult


@admin.register(LearningResult)
class LearningResultAdmin(admin.ModelAdmin):
    list_display = ["id", "get_username", "get_title", "get_mode", "watch_rate", "total_score", "max_combo", "typing_accuracy", "quiz_correct", "quiz_total", "tab_switch_count", "study_duration_seconds", "completed_at"]
    list_filter = ["session__mode", "completed_at"]
    search_fields = ["session__title", "session__user__username"]

    def get_username(self, obj):
        return obj.session.user.username
    get_username.short_description = "유저"

    def get_title(self, obj):
        return obj.session.title
    get_title.short_description = "영상 제목"

    def get_mode(self, obj):
        return obj.session.mode
    get_mode.short_description = "모드"