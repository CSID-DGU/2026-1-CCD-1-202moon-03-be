import secrets
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from common.response import success_response, error_response
from .serializers import (
    RegisterSerializer, LoginSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    SurveySerializer,
)
from .models import PasswordResetToken, SurveyAnswer

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("입력값이 올바르지 않습니다.", serializer.errors, status=400)
        user = serializer.save()
        return success_response("회원가입이 완료되었습니다.", {
            "user_id": user.id,
            "username": user.username,
            "nickname": user.nickname,
        }, status=201)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("아이디 또는 비밀번호가 올바르지 않습니다.", status=401)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return success_response("로그인이 완료되었습니다.", {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "user_id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "is_tutorial_done": user.is_tutorial_done,
            },
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return error_response("refresh 토큰이 필요합니다.", status=400)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return error_response("유효하지 않은 토큰입니다.", status=400)
        return success_response("로그아웃이 완료되었습니다.")


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return error_response("refresh 토큰이 필요합니다.", status=400)
        try:
            token = RefreshToken(refresh_token)
            return success_response("토큰이 재발급되었습니다.", {
                "access": str(token.access_token)
            })
        except TokenError:
            return error_response("토큰이 만료되었거나 유효하지 않습니다.", status=401)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("이메일 형식이 올바르지 않습니다.", status=400)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email=email, is_active=True).first()
        if user:
            PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
            token_value = secrets.token_urlsafe(32)
            PasswordResetToken.objects.create(
                user=user,
                token=token_value,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            reset_url = f"http://localhost:3000/reset-password?token={token_value}"
            try:
                send_mail(
                    subject="[TADAC] 비밀번호 재설정",
                    message=f"아래 링크를 클릭해 비밀번호를 재설정하세요.\n\n{reset_url}\n\n링크는 10분 후 만료됩니다.",
                    from_email=settings.EMAIL_HOST_USER or "noreply@tadac.com",
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception:
                return error_response("메일 발송에 실패했습니다. 다시 시도해주세요.", status=500)
        return success_response("메일 발송이 완료되었습니다.")


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("입력값이 올바르지 않습니다.", serializer.errors, status=400)
        token_value = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]
        try:
            reset_token = PasswordResetToken.objects.select_related("user").get(token=token_value)
        except PasswordResetToken.DoesNotExist:
            return error_response("유효하지 않은 재설정 링크입니다.", status=400)
        if not reset_token.is_valid():
            return error_response("재설정 링크가 만료되었습니다.", status=400)
        user = reset_token.user
        user.set_password(new_password)
        user.save()
        reset_token.is_used = True
        reset_token.save()
        return success_response("비밀번호가 변경되었습니다.")


class SurveyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SurveySerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("입력값이 올바르지 않습니다.", serializer.errors, status=400)
        answers = serializer.validated_data["answers"]
        user = request.user
        SurveyAnswer.objects.filter(user=user).delete()
        SurveyAnswer.objects.bulk_create([
            SurveyAnswer(
                user=user,
                question_number=a["question_number"],
                answer_value=a["answer_value"],
            )
            for a in answers
        ])
        level = serializer.calculate_stimulation_level(answers)
        user.stimulation_level = level
        user.save(update_fields=["stimulation_level"])
        return success_response("설문이 완료되었습니다.", {"stimulation_level": level}, status=201)