from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from common.response import success_response, error_response
from sessions.models import VideoSession, Subtitle, FallEvent
from sessions.serializers import SubtitleSerializer, FallEventSerializer
from quiz.models import Quiz
from .serializers import (
    SubtitleGameSerializer,
    FallEventGameSerializer,
    QuizGameSerializer,
    GameEndSerializer,
)


def get_session_or_404(pk, user):
    try:
        return VideoSession.objects.get(id=pk, user=user)
    except VideoSession.DoesNotExist:
        return None


class GameStartView(APIView):
    """
    POST /api/sessions/{id}/game/start/
    게임 시작 — 자막/낙하이벤트/퀴즈 전체 데이터 한 번에 반환
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        session = get_session_or_404(pk, request.user)
        if not session:
            return error_response("세션을 찾을 수 없습니다.", status=404)

        # AI 처리 완료된 세션만 게임 시작 가능
        if session.ai_status != VideoSession.AI_DONE:
            return error_response(
                "AI 처리가 완료되지 않았습니다.",
                {"ai_status": session.ai_status},
                status=400,
            )

        # 자막 + 빈칸 데이터
        subtitles = Subtitle.objects.prefetch_related("blanks").filter(
            session=session
        )
        subtitles_data = []
        for s in subtitles:
            subtitles_data.append({
                "segment_id": s.segment_id,
                "start_sec": s.start_sec,
                "end_sec": s.end_sec,
                "original_text": s.original_text,
                "blank_text": s.blank_text,
                "blanks": [
                    {
                        "keyword": b.keyword,
                        "position": b.position,
                        "answer_length": b.answer_length,
                    }
                    for b in s.blanks.all()
                ],
            })

        # 퀴즈 데이터
        quizzes = Quiz.objects.filter(session=session)
        quizzes_data = [
            {
                "quiz_id": q.id,
                "quiz_index": q.quiz_index,
                "trigger_time": q.trigger_time,
                "question": q.question,
                "options": q.options_json,
                "answer_index": q.answer_index,
                "explanation": q.explanation,
            }
            for q in quizzes
        ]

        data = {
            "session_id": session.id,
            "mode": session.mode,
            "duration_sec": session.duration_sec,
            "subtitles": subtitles_data,
            "quizzes": quizzes_data,
        }

        # 집중호우 모드면 낙하 이벤트 추가
        if session.mode == VideoSession.MODE_RAIN:
            fall_events = FallEvent.objects.select_related("subtitle").filter(
                session=session
            )
            data["fall_events"] = [
                {
                    "keyword": fe.keyword,
                    "target_time": fe.target_time,
                    "fall_window": fe.fall_window,
                    "segment_id": fe.subtitle.segment_id,
                }
                for fe in fall_events
            ]

        return success_response("게임 시작", data)


class GameEndView(APIView):
    """
    POST /api/sessions/{id}/game/end/
    게임 종료 — 학습 결과 저장
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        session = get_session_or_404(pk, request.user)
        if not session:
            return error_response("세션을 찾을 수 없습니다.", status=404)

        serializer = GameEndSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                "입력값이 올바르지 않습니다.", serializer.errors, status=400
            )

        from analytics.models import LearningResult

        # 이미 결과 있으면 업데이트, 없으면 생성
        result, created = LearningResult.objects.update_or_create(
            session=session,
            defaults={
                "watch_rate": serializer.validated_data["watch_rate"],
                "total_score": serializer.validated_data["total_score"],
                "max_combo": serializer.validated_data["max_combo"],
                "typing_accuracy": serializer.validated_data["typing_accuracy"],
                "quiz_correct": serializer.validated_data["quiz_correct"],
                "quiz_total": serializer.validated_data["quiz_total"],
                "tab_switch_count": serializer.validated_data.get("tab_switch_count", 0),
            },
        )

        return success_response(
            "학습 결과가 저장되었습니다.",
            {
                "result_id": result.id,
                "session_id": session.id,
                "watch_rate": result.watch_rate,
                "total_score": result.total_score,
                "max_combo": result.max_combo,
                "typing_accuracy": result.typing_accuracy,
                "quiz_correct": result.quiz_correct,
                "quiz_total": result.quiz_total,
                "tab_switch_count": result.tab_switch_count,
                "completed_at": result.completed_at,
            },
            status=201 if created else 200,
        )