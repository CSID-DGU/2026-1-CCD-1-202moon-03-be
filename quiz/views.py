from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from common.response import success_response, error_response
from sessions.models import VideoSession
from .models import Quiz, QuizAttempt
from .serializers import QuizAnswerSerializer, QuizRetrySerializer


def get_session_or_404(pk, user):
    try:
        return VideoSession.objects.get(id=pk, user=user)
    except VideoSession.DoesNotExist:
        return None


class QuizAnswerView(APIView):
    """
    POST /api/sessions/{id}/quiz/{qid}/answer/
    퀴즈 답안 제출 → 정답/오답 즉시 반환
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, qid):
        session = get_session_or_404(pk, request.user)
        if not session:
            return error_response("세션을 찾을 수 없습니다.", status=404)

        # 퀴즈 존재 확인
        try:
            quiz = Quiz.objects.get(id=qid, session=session)
        except Quiz.DoesNotExist:
            return error_response("퀴즈를 찾을 수 없습니다.", status=404)

        serializer = QuizAnswerSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                "유효하지 않은 선택지입니다.", serializer.errors, status=400
            )

        selected_index = serializer.validated_data["selected_index"]
        is_correct = selected_index == quiz.answer_index

        # LearningResult 있으면 QuizAttempt 기록
        try:
            result = session.result
            QuizAttempt.objects.create(
                result=result,
                quiz=quiz,
                selected_index=selected_index,
                is_correct=is_correct,
            )
        except Exception:
            # 게임 종료 전에 퀴즈 제출하는 경우 — 기록 안 해도 됨
            pass

        if is_correct:
            return success_response("정답입니다!", {
                "is_correct": True,
                "answer_index": quiz.answer_index,
                "explanation": quiz.explanation,
            })
        else:
            return success_response("오답입니다.", {
                "is_correct": False,
                "answer_index": quiz.answer_index,
                "explanation": quiz.explanation,
            })


class QuizRetryView(APIView):
    """
    GET /api/sessions/{id}/quiz/retry/
    퀴즈 다시 풀기 — explanation 제외하고 반환
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        session = get_session_or_404(pk, request.user)
        if not session:
            return error_response("세션을 찾을 수 없습니다.", status=404)

        quizzes = Quiz.objects.filter(session=session)
        serializer = QuizRetrySerializer(quizzes, many=True)

        return success_response("퀴즈 목록 조회 성공", {
            "session_id": session.id,
            "quizzes": serializer.data,
        })