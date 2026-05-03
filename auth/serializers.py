import re
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "password", "nickname", "email",
                  "birth_date", "gender"]
        extra_kwargs = {
            "email": {"required": True},
        }

    def validate_username(self, value):
        if not re.match(r'^[a-zA-Z0-9_]{4,20}$', value):
            raise serializers.ValidationError(
                "아이디는 4~20자, 영문/숫자/밑줄만 사용 가능합니다."
            )
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("이미 사용 중인 아이디입니다.")
        return value

    def validate_nickname(self, value):
        if not (2 <= len(value) <= 15):
            raise serializers.ValidationError("닉네임은 2~15자 이내로 입력해주세요.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("이미 사용 중인 이메일입니다.")
        return value

    def validate_password(self, value):
        if not re.search(r'[a-zA-Z]', value):
            raise serializers.ValidationError("비밀번호는 영문자를 포함해야 합니다.")
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError("비밀번호는 숫자를 포함해야 합니다.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            nickname=validated_data["nickname"],
            birth_date=validated_data.get("birth_date"),
            gender=validated_data.get("gender"),
        )
        from users.models import UserSetting
        UserSetting.objects.create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        from django.contrib.auth import authenticate
        user = authenticate(username=data["username"], password=data["password"])
        if not user:
            raise serializers.ValidationError(
                "아이디 또는 비밀번호가 올바르지 않습니다."
            )
        if not user.is_active:
            raise serializers.ValidationError("비활성화된 계정입니다.")
        data["user"] = user
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    new_password_confirm = serializers.CharField()

    def validate(self, data):
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


class SurveyAnswerItemSerializer(serializers.Serializer):
    question_number = serializers.IntegerField(min_value=1, max_value=5)
    answer_value = serializers.CharField(max_length=100)


class SurveySerializer(serializers.Serializer):
    answers = SurveyAnswerItemSerializer(many=True)

    def validate_answers(self, value):
        if len(value) != 5:
            raise serializers.ValidationError("설문 문항은 5개 모두 답변해야 합니다.")
        question_numbers = [a["question_number"] for a in value]
        if sorted(question_numbers) != [1, 2, 3, 4, 5]:
            raise serializers.ValidationError("문항 번호가 올바르지 않습니다.")
        return value

    def calculate_stimulation_level(self, answers: list) -> int:
        high_count = sum(1 for a in answers if a["answer_value"] == "high")
        if high_count >= 3:
            return 3
        elif high_count >= 1:
            return 2
        return 1