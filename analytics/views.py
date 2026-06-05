from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncDate, TruncWeek
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from common.response import success_response, error_response
from .models import LearningResult
from sessions.models import VideoSession


class LearningResultDetailView(APIView):
    """
    GET /api/analytics/sessions/{id}/result/
    세션 학습 결과 조회 (tab_leave_count, study_duration_seconds 포함)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            session = VideoSession.objects.get(id=pk, user=request.user)
        except VideoSession.DoesNotExist:
            return error_response("세션을 찾을 수 없습니다.", status=404)

        try:
            result = session.result
        except Exception:
            return error_response("학습 결과를 찾을 수 없습니다.", status=404)

        return success_response("학습 결과 조회 성공", {
            "session_id": session.id,
            "title": session.title,
            "mode": session.mode,
            "thumbnail_url": session.thumbnail_url,
            "watch_rate": result.watch_rate,
            "total_score": result.total_score,
            "max_combo": result.max_combo,
            "typing_accuracy": result.typing_accuracy,
            "quiz_correct": result.quiz_correct,
            "quiz_total": result.quiz_total,
            "tab_leave_count": result.tab_switch_count,
            "study_duration_seconds": result.study_duration_seconds,
            "completed_at": result.completed_at,
        })


class LearningDashboardView(APIView):
    """
    GET /api/analytics/dashboard/
    마이페이지 전체 학습 기록 + 대시보드 집계값
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        results = LearningResult.objects.filter(
            session__user=request.user
        ).select_related("session").order_by("-completed_at")

        if not results.exists():
            return success_response("학습 기록 없음", {
                "summary": {},
                "trends": {},
                "focus_stats": {},
                "daily_results": [],
                "sessions": [],
            })

        # ── summary ──────────────────────────────────────────────
        agg = results.aggregate(
            total_duration=Sum("study_duration_seconds"),
            avg_quiz=Avg("quiz_correct") ,
            avg_typing=Avg("typing_accuracy"),
            avg_tab=Avg("tab_switch_count"),
        )

        # 평균 정답률 계산 (quiz_correct/quiz_total)
        total_correct = sum(r.quiz_correct for r in results)
        total_quiz = sum(r.quiz_total for r in results)
        avg_quiz_accuracy = round(total_correct / total_quiz * 100, 1) if total_quiz > 0 else 0

        summary = {
            "total_study_duration_seconds": agg["total_duration"] or 0,
            "average_quiz_accuracy": avg_quiz_accuracy,
            "average_typing_accuracy": round(agg["avg_typing"] or 0, 1),
            "average_tab_leave_count": round(agg["avg_tab"] or 0, 1),
        }

        # ── trends ───────────────────────────────────────────────
        daily_data = results.annotate(date=TruncDate("completed_at")).values("date").annotate(
            total_duration=Sum("study_duration_seconds"),
        ).order_by("date")

        weekly_data = results.annotate(week=TruncWeek("completed_at")).values("week").annotate(
            correct=Sum("quiz_correct"),
            total=Sum("quiz_total"),
            avg_typing=Avg("typing_accuracy"),
        ).order_by("week")

        trends = {
            "study_time": [
                {"date": str(d["date"]), "seconds": d["total_duration"] or 0}
                for d in daily_data
            ],
            "quiz_accuracy": [
                {
                    "week": str(w["week"]),
                    "accuracy": round(w["correct"] / w["total"] * 100, 1) if w["total"] else 0
                }
                for w in weekly_data
            ],
            "typing_accuracy": [
                {"week": str(w["week"]), "accuracy": round(w["avg_typing"] or 0, 1)}
                for w in weekly_data
            ],
        }

        # ── focus_stats ───────────────────────────────────────────
        now = timezone.now()
        this_week_start = now - timedelta(days=now.weekday())
        last_week_start = this_week_start - timedelta(weeks=1)

        this_week_tab = results.filter(
            completed_at__gte=this_week_start
        ).aggregate(total=Sum("tab_switch_count"))["total"] or 0

        last_week_tab = results.filter(
            completed_at__gte=last_week_start,
            completed_at__lt=this_week_start,
        ).aggregate(total=Sum("tab_switch_count"))["total"] or 0

        if last_week_tab > 0:
            change_rate = round((this_week_tab - last_week_tab) / last_week_tab * 100, 1)
        else:
            change_rate = 0

        focus_stats = {
            "this_week_tab_leave_count": this_week_tab,
            "tab_leave_change_rate": change_rate,
        }

        # ── daily_results ─────────────────────────────────────────
        daily_results_qs = results.annotate(date=TruncDate("completed_at")).values("date").annotate(
            session_count=Count("id"),
            total_study_duration_seconds=Sum("study_duration_seconds"),
            total_correct=Sum("quiz_correct"),
            total_quiz=Sum("quiz_total"),
            average_typing_accuracy=Avg("typing_accuracy"),
            total_tab_leave_count=Sum("tab_switch_count"),
        ).order_by("-date")

        daily_results = [
            {
                "date": str(d["date"]),
                "session_count": d["session_count"],
                "total_study_duration_seconds": d["total_study_duration_seconds"] or 0,
                "average_quiz_accuracy": round(d["total_correct"] / d["total_quiz"] * 100, 1) if d["total_quiz"] else 0,
                "average_typing_accuracy": round(d["average_typing_accuracy"] or 0, 1),
                "total_tab_leave_count": d["total_tab_leave_count"] or 0,
            }
            for d in daily_results_qs
        ]

        # ── sessions ──────────────────────────────────────────────
        sessions_data = [
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
                "tab_leave_count": r.tab_switch_count,
                "study_duration_seconds": r.study_duration_seconds,
                "completed_at": r.completed_at,
            }
            for r in results
        ]

        return success_response("대시보드 조회 성공", {
            "summary": summary,
            "trends": trends,
            "focus_stats": focus_stats,
            "daily_results": daily_results,
            "sessions": sessions_data,
        })