from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import UserSetting

User = get_user_model()

# 허용된 아바타 목록
AVATAR_CHOICES = [
    "character_1", "character_2", "character_3",
    "character_4", "character_5", "character_6",
    "character_7", "character_8",
]

# 허용된 키 목록
KEY_CHOICES = ["alt", "ctrl", "shift", "tab"]


class UserProfileSerializer(serializers.ModelSerializer):
    """GET /api/users/me/ — 프로필 조회"""
    class Meta:
        model = User
        fields = [
            "id", "username", "email", "nickname",
            "avatar_type", "stimulation_level",
            "is_tutorial_done", "created_at",
        ]
        read_only_fields = fields


class UserUpdateSerializer(serializers.ModelSerializer):
    """PATCH /api/users/me/ — 프로필 수정 (닉네임, 아바타만)"""
    class Meta:
        model = User
        fields = ["nickname", "avatar_type"]

    def validate_nickname(self, value):
        if not (2 <= len(value) <= 15):
            raise serializers.ValidationError("닉네임은 2~15자 이내로 입력해주세요.")
        return value

    def validate_avatar_type(self, value):
        if value not in AVATAR_CHOICES:
            raise serializers.ValidationError("허용되지 않는 아바타입니다.")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """PUT /api/users/me/password/ — 비밀번호 변경"""
    current_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    new_password_confirm = serializers.CharField()

    def validate(self, data):
        import re
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "비밀번호가 일치하지 않습니다."}
            )
        if not re.search(r'[a-zA-Z]', data["new_password"]):
            raise serializers.ValidationError(
                {"new_password": "비밀번호 형식이 올바르지 않습니다."}
            )
        if not re.search(r'[0-9]', data["new_password"]):
            raise serializers.ValidationError(
                {"new_password": "비밀번호 형식이 올바르지 않습니다."}
            )
        return data


class UserSettingSerializer(serializers.ModelSerializer):
    """GET·PATCH /api/users/me/settings/"""
    class Meta:
        model = UserSetting
        fields = ["fidget_toggle_key"]

    def validate_fidget_toggle_key(self, value):
        if value not in KEY_CHOICES:
            raise serializers.ValidationError(
                f"허용되지 않는 키값입니다. 가능한 값: {KEY_CHOICES}"
            )
        return value