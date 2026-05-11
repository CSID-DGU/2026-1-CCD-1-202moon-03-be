from rest_framework import serializers
from sessions.models import Subtitle, FallEvent
from quiz.models import Quiz


class BlankItemSerializer(serializers.Serializer):
    keyword = serializers.CharField()
    position = serializers.IntegerField()
    answer_length = serializers.IntegerField()


class SubtitleGameSerializer(serializers.Serializer):
    segment_id = serializers.IntegerField()
    start_sec = serializers.FloatField()
    end_sec = serializers.FloatField()
    original_text = serializers.CharField()
    blank_text = serializers.CharField()
    blanks = BlankItemSerializer(many=True)


class FallEventGameSerializer(serializers.Serializer):
    keyword = serializers.CharField()
    target_time = serializers.FloatField()
    fall_window = serializers.FloatField()
    segment_id = serializers.IntegerField(source="subtitle.segment_id")


class QuizGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = [
            "id", "quiz_index", "trigger_time",
            "question", "options_json",
            "answer_index", "explanation",
        ]


class GameEndSerializer(serializers.Serializer):
    watch_rate = serializers.FloatField(min_value=0.0, max_value=1.0)
    total_score = serializers.IntegerField(default=0)
    max_combo = serializers.IntegerField(default=0)
    typing_accuracy = serializers.FloatField(
        min_value=0.0, max_value=1.0, default=0.0
    )
    quiz_correct = serializers.IntegerField(default=0)
    quiz_total = serializers.IntegerField(default=0)
    tab_switch_count = serializers.IntegerField(default=0)  # ← 추가