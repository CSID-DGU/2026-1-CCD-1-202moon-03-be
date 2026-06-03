from django.contrib import admin
from .models import Quiz


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "quiz_index", "trigger_time", "question", "answer_index"]
    search_fields = ["session__title", "question"]
    list_filter = ["session__mode"]