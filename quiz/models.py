from django.db import models
from sessions.models import VideoSession


class Quiz(models.Model):
    session = models.ForeignKey(
        VideoSession, on_delete=models.CASCADE, related_name="quizzes"
    )
    quiz_index = models.IntegerField()
    trigger_time = models.FloatField()
    segment_start = models.IntegerField()
    segment_end = models.IntegerField()
    question = models.TextField()
    options_json = models.JSONField()   # ["선택1", "선택2", "선택3", "선택4"]
    answer_index = models.IntegerField()
    explanation = models.TextField()

    class Meta:
        db_table = "quiz"
        ordering = ["quiz_index"]


class QuizAttempt(models.Model):
    result = models.ForeignKey(
        "analytics.LearningResult",
        on_delete=models.CASCADE,
        related_name="quiz_attempts"
    )
    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="attempts"
    )
    selected_index = models.IntegerField()
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quiz_attempt"