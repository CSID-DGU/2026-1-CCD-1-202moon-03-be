from rest_framework import serializers
from .models import VideoSession, Subtitle, BlankItem, FallEvent


class BlankItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlankItem
        fields = ["keyword", "position", "answer_length"]


class SubtitleSerializer(serializers.ModelSerializer):
    blanks = BlankItemSerializer(many=True, read_only=True)

    class Meta:
        model = Subtitle
        fields = ["segment_id", "start_sec", "end_sec",
                  "original_text", "blank_text", "blanks"]


class FallEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = FallEvent
        fields = ["keyword", "target_time", "fall_window"]


class SessionListSerializer(serializers.ModelSerializer):
    """목록 조회용 — 가벼운 데이터만"""
    class Meta:
        model = VideoSession
        fields = [
            "id", "title", "thumbnail_url",
            "mode", "ai_status", "created_at",
        ]


class SessionCreateSerializer(serializers.ModelSerializer):
    """세션 생성용"""
    class Meta:
        model = VideoSession
        fields = ["source_type", "source_url", "mode", "title"]
        extra_kwargs = {
            "title": {"required": False},  # 유튜브면 자동으로 가져올 예정
            "source_url": {"required": False},
        }

    def validate(self, data):
        source_type = data.get("source_type")
        source_url = data.get("source_url")

        if source_type in ["youtube_url", "private_url"] and not source_url:
            raise serializers.ValidationError(
                {"source_url": "URL을 입력해주세요."}
            )
        # 유튜브 URL 형식 검사
        if source_type == "youtube_url" and source_url:
            if "youtube.com" not in source_url and "youtu.be" not in source_url:
                raise serializers.ValidationError(
                    {"source_url": "지원하지 않는 영상 URL입니다."}
                )
        return data


class SessionDetailSerializer(serializers.ModelSerializer):
    """상세 조회용"""
    class Meta:
        model = VideoSession
        fields = [
            "id", "title", "source_type", "source_url",
            "thumbnail_url", "duration_sec", "mode",
            "ai_status", "created_at",
        ]


class SessionTitleUpdateSerializer(serializers.ModelSerializer):
    """제목 수정용"""
    class Meta:
        model = VideoSession
        fields = ["title"]