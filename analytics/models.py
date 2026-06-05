from django.db import models
from sessions.models import VideoSession


class LearningResult(models.Model):
    session = models.OneToOneField(
        VideoSession, on_delete=models.CASCADE, related_name="result"
    )
    watch_rate = models.FloatField(default=0.0)
    total_score = models.IntegerField(default=0)     # 집중호우 모드만
    max_combo = models.IntegerField(default=0)       # 집중호우 모드만
    typing_accuracy = models.FloatField(default=0.0) # 집중호우 모드만
    quiz_correct = models.IntegerField(default=0)
    quiz_total = models.IntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)
    tab_switch_count = models.IntegerField(default=0)
    study_duration_seconds = models.IntegerField(default=0)

    class Meta:
        db_table = "learning_result"