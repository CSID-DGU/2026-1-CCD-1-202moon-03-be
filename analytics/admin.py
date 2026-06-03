from django.contrib import admin
from .models import LearningResult


@admin.register(LearningResult)
class LearningResultAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "watch_rate", "total_score", "max_combo", "typing_accuracy", "quiz_correct", "quiz_total", "completed_at"]
    search_fields = ["session__title", "session__user__username"]