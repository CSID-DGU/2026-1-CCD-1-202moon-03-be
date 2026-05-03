import httpx
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def process_video_pipeline(session_id: int):
    """
    AI 서버(FastAPI)로 영상 처리를 위임하고 결과를 DB에 저장.
    
    ※ 지금은 Celery 없이 일반 함수로 작성
    ※ Redis 설치 후 아래처럼 바꿀 예정
    
    from project.celery import app
    
    @app.task(bind=True, max_retries=3)
    def process_video_pipeline(self, session_id: int):
        ...
    """
    from sessions.models import VideoSession, Subtitle, BlankItem, FallEvent
    from quiz.models import Quiz

    try:
        session = VideoSession.objects.get(id=session_id)

        # 처리 중으로 상태 변경
        session.ai_status = VideoSession.AI_PROCESSING
        session.save(update_fields=["ai_status"])

        # AI 서버로 요청 보내기
        payload = {"language": "ko", "refine": True}
        if session.source_url:
            payload["source_url"] = session.source_url

        with httpx.Client(timeout=settings.AI_SERVER_TIMEOUT) as client:
            response = client.post(
                f"{settings.AI_SERVER_URL}/pipeline/",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        # ── 자막 저장 ──────────────────────────────────────
        subtitles_map = {}
        for s in data.get("subtitles", []):
            subtitle = Subtitle.objects.create(
                session=session,
                segment_id=s["segment_id"],
                start_sec=s["start"],
                end_sec=s["end"],
                original_text=s["original_text"],
                blank_text=s["blank_text"],
            )
            subtitles_map[s["segment_id"]] = subtitle

            # 빈칸 아이템 저장
            for b in s.get("blanks", []):
                BlankItem.objects.create(
                    subtitle=subtitle,
                    keyword=b["keyword"],
                    position=b["position"],
                    answer_length=b["answer_length"],
                )

        # ── 낙하 이벤트 저장 ───────────────────────────────
        for fe in data.get("fall_events", []):
            FallEvent.objects.create(
                session=session,
                subtitle=subtitles_map[fe["segment_id"]],
                keyword=fe["keyword"],
                target_time=fe["target_time"],
                fall_window=fe["fall_window"],
            )

        # ── 퀴즈 저장 ──────────────────────────────────────
        for q in data.get("quizzes", []):
            Quiz.objects.create(
                session=session,
                quiz_index=q["quiz_id"],
                trigger_time=q["trigger_time"],
                segment_start=q["segment_range"][0],
                segment_end=q["segment_range"][1],
                question=q["question"],
                options_json=q["options"],
                answer_index=q["answer_index"],
                explanation=q["explanation"],
            )

        # 완료 처리
        session.ai_status = VideoSession.AI_DONE
        session.save(update_fields=["ai_status"])
        logger.info(f"[AI Pipeline] session {session_id} 처리 완료")

    except VideoSession.DoesNotExist:
        logger.error(f"[AI Pipeline] session {session_id} 없음")

    except Exception as exc:
        logger.error(f"[AI Pipeline] session {session_id} 실패: {exc}")
        try:
            session = VideoSession.objects.get(id=session_id)
            session.ai_status = VideoSession.AI_FAILED
            session.ai_error_message = str(exc)
            session.save(update_fields=["ai_status", "ai_error_message"])
        except Exception:
            pass