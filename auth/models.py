from django.db import models
from django.conf import settings


class SurveyAnswer(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="survey_answers"
    )
    question_number = models.IntegerField()
    answer_value = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "survey_answer"
        unique_together = ("user", "question_number")


class PasswordResetToken(models.Model):
    """비밀번호 찾기용 임시 토큰 (10분 유효)"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reset_tokens"
    )
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "password_reset_token"

    def is_valid(self):
        """토큰이 유효한지 확인 (만료 안 됐고, 사용 안 됐는지)"""
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()