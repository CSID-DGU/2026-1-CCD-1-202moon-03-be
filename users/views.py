from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from common.response import success_response, error_response
from .serializers import (
    UserProfileSerializer,
    UserUpdateSerializer,
    PasswordChangeSerializer,
    UserSettingSerializer,
)

User = get_user_model()


class UserProfileView(APIView):
    """
    GET  /api/users/me/ — 프로필 조회
    PATCH /api/users/me/ — 닉네임/아바타 수정
    DELETE /api/users/me/ — 회원 탈퇴
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return success_response("프로필 조회 성공", serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,  # 부분 수정 허용
        )
        if not serializer.is_valid():
            return error_response("입력값이 올바르지 않습니다.", serializer.errors, status=400)
        serializer.save()
        return success_response("프로필이 수정되었습니다.", serializer.data)

    def delete(self, request):
        # 비밀번호 재확인
        password = request.data.get("password")
        if not password:
            return error_response("비밀번호를 입력해주세요.", status=400)
        if not request.user.check_password(password):
            return error_response("비밀번호가 올바르지 않습니다.", status=400)

        # 소프트 딜리트 (실제 삭제 아님 — is_active=False 로 비활성화)
        request.user.is_active = False
        request.user.save(update_fields=["is_active"])
        return success_response("회원 탈퇴가 완료되었습니다.")


class PasswordChangeView(APIView):
    """
    PUT /api/users/me/password/
    기존 비밀번호 확인 → 새 비밀번호 변경 → 새 토큰 재발급
    """
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("입력값이 올바르지 않습니다.", serializer.errors, status=400)

        # 현재 비밀번호 확인
        if not request.user.check_password(serializer.validated_data["current_password"]):
            return error_response("현재 비밀번호가 올바르지 않습니다.", status=400)

        # 새 비밀번호 저장
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()

        # 토큰 재발급 (로그인 유지)
        refresh = RefreshToken.for_user(request.user)
        return success_response("비밀번호가 변경되었습니다.", {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })


class UserSettingView(APIView):
    """
    GET   /api/users/me/settings/ — 환경설정 조회
    PATCH /api/users/me/settings/ — 환경설정 수정
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # UserSetting 없으면 기본값으로 자동 생성
        setting, _ = request.user.setting.__class__.objects.get_or_create(
            user=request.user,
            defaults={"fidget_toggle_key": "alt"},
        )
        serializer = UserSettingSerializer(setting)
        return success_response("환경설정 조회 성공", serializer.data)

    def patch(self, request):
        setting, _ = request.user.setting.__class__.objects.get_or_create(
            user=request.user,
            defaults={"fidget_toggle_key": "alt"},
        )
        serializer = UserSettingSerializer(setting, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("입력값이 올바르지 않습니다.", serializer.errors, status=400)
        serializer.save()
        return success_response("환경설정이 변경되었습니다.", serializer.data)


class LearningHistoryView(APIView):
    """
    GET /api/users/me/history/
    마이페이지 전체 학습 기록 목록
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from analytics.models import LearningResult
        results = LearningResult.objects.filter(
            session__user=request.user
        ).select_related("session").order_by("-completed_at")

        data = [
            {
                "session_id": r.session.id,
                "title": r.session.title,
                "mode": r.session.mode,
                "thumbnail_url": r.session.thumbnail_url,
                "watch_rate": r.watch_rate,
                "total_score": r.total_score,
                "typing_accuracy": r.typing_accuracy,
                "quiz_correct": r.quiz_correct,
                "quiz_total": r.quiz_total,
                "completed_at": r.completed_at,
            }
            for r in results
        ]
        return success_response("학습 기록 조회 성공", data)