from rest_framework import serializers
from .models import Quiz, QuizAttempt


class QuizAnswerSerializer(serializers.Serializer):
    """퀴즈 답안 제출용"""
    selected_index = serializers.IntegerField(min_value=0, max_value=3)


class QuizRetrySerializer(serializers.ModelSerializer):
    """퀴즈 다시 풀기용 — explanation 제외"""
    options = serializers.JSONField(source="options_json")

    class Meta:
        model = Quiz
        fields = [
            "id", "quiz_index", "trigger_time",
            "question", "options",
        ]