import json
import httpx
from django.http import StreamingHttpResponse, HttpResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from common.response import success_response, error_response
from .models import VideoSession, Subtitle, FallEvent
from .serializers import (
    SessionListSerializer,
    SessionCreateSerializer,
    SessionDetailSerializer,
    SessionTitleUpdateSerializer,
    SubtitleSerializer,
    FallEventSerializer,
)


def get_session_or_404(pk, user):
    """본인 세션만 가져오는 헬퍼 함수"""
    try:
        return VideoSession.objects.get(id=pk, user=user)
    except VideoSession.DoesNotExist:
        return None


class SessionListCreateView(APIView):
    """
    GET  /api/sessions/     — 학습 영상 목록 조회
    POST /api/sessions/     — 새 세션 생성
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = VideoSession.objects.filter(user=request.user)
        serializer = SessionListSerializer(sessions, many=True)
        return success_response("학습 목록 조회 성공", serializer.data)

    def post(self, request):
        serializer = SessionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("입력값이 올바르지 않습니다.", serializer.errors, status=400)

        source_type = serializer.validated_data["source_type"]
        source_url = serializer.validated_data.get("source_url", "")
        mode = serializer.validated_data["mode"]

        title = serializer.validated_data.get("title") or "새 학습 영상"
        thumbnail_url = None
        file_path = None

        # ── 유튜브 URL인 경우 → 제목/썸네일 자동 추출 ──────────────
        if source_type == VideoSession.SOURCE_YOUTUBE and source_url:
            try:
                import yt_dlp
                ydl_opts = {"quiet": True, "skip_download": True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(source_url, download=False)
                    title = info.get("title", title)
                    thumbnail_url = info.get("thumbnail")
            except Exception:
                # 실패해도 세션 생성은 진행
                pass

        # ── 파일 업로드인 경우 → file_path 저장 ───────────────────
        if source_type == VideoSession.SOURCE_FILE:
            file = request.FILES.get("file")
            if not file:
                return error_response("파일을 업로드해주세요.", status=400)

            import os
            from django.conf import settings as django_settings

            save_dir = os.path.join(django_settings.MEDIA_ROOT, "videos")
            os.makedirs(save_dir, exist_ok=True)

            file_name = f"{request.user.id}_{file.name}"
            file_full_path = os.path.join(save_dir, file_name)

            with open(file_full_path, "wb") as f:
                for chunk in file.chunks():
                    f.write(chunk)

            file_path = f"{django_settings.MEDIA_URL}videos/{file_name}"

            # ── 로컬 파일 제목 추출 ──────────────────────────────
            # 확장자 제거해서 제목으로 사용
            original_name = os.path.splitext(file.name)[0]
            title = original_name if original_name else "새 학습 영상"

            # 썸네일은 로컬 파일에서 추출 불가 → null 유지
            # (ffmpeg 설치 시 추출 가능하나 현재 미설치)
            thumbnail_url = None

        # ── 세션 생성 ──────────────────────────────────────────────
        session = VideoSession.objects.create(
            user=request.user,
            title=title,
            source_type=source_type,
            source_url=source_url if source_url else None,
            file_path=file_path,
            thumbnail_url=thumbnail_url,
            mode=mode,
            ai_status=VideoSession.AI_PENDING,
        )

        return success_response(
            "세션이 생성되었습니다. AI 처리를 시작합니다.",
            {
                "session_id": session.id,
                "title": session.title,
                "thumbnail_url": session.thumbnail_url,
                "source_url": session.source_url,
                "file_path": session.file_path,
                "ai_status": session.ai_status,
                "mode": session.mode,
            },
            status=201,
        )


class SessionDetailView(APIView):
    """
    GET    /api/sessions/{id}/ — 세션 상세 조회
    PATCH  /api/sessions/{id}/ — 제목 수정
    DELETE /api/sessions/{id}/ — 세션 삭제
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        session = get_session_or_404(pk, request.user)
        if not session:
            return error_response("세션을 찾을 수 없습니다.", status=404)
        serializer = SessionDetailSerializer(session)
        return success_response("세션 조회 성공", serializer.data)

    def patch(self, request, pk):
        session = get_session_or_404(pk, request.user)
        if not session:
            return error_response("세션을 찾을 수 없습니다.", status=404)
        serializer = SessionTitleUpdateSerializer(
            session, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return error_response("입력값이 올바르지 않습니다.", serializer.errors, status=400)
        serializer.save()
        return success_response("제목이 수정되었습니다.", {
            "session_id": session.id,
            "title": serializer.validated_data["title"],
        })

    def delete(self, request, pk):
        session = get_session_or_404(pk, request.user)
        if not session:
            return error_response("세션을 찾을 수 없습니다.", status=404)
        session.delete()  # cascade로 관련 데이터 전부 삭제
        return success_response("세션이 삭제되었습니다.")


class SessionStatusView(APIView):
    """
    GET /api/sessions/{id}/status/ — AI 처리 상태 폴링
    프론트에서 3~5초마다 호출해서 완료 여부 확인
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        session = get_session_or_404(pk, request.user)
        if not session:
            return error_response("세션을 찾을 수 없습니다.", status=404)

        data = {
            "session_id": session.id,
            "ai_status": session.ai_status,
        }
        if session.ai_status == VideoSession.AI_FAILED:
            data["error_message"] = session.ai_error_message

        return success_response("상태 조회 성공", data)


class SessionResultView(APIView):
    """
    GET /api/sessions/{id}/result/ — 학습 결과 조회
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        session = get_session_or_404(pk, request.user)
        if not session:
            return error_response("세션을 찾을 수 없습니다.", status=404)

        try:
            result = session.result  # LearningResult OneToOne
        except Exception:
            return error_response("학습 결과를 찾을 수 없습니다.", status=404)

        return success_response("학습 결과 조회 성공", {
            "session_id": session.id,
            "mode": session.mode,
            "title": session.title,
            "watch_rate": result.watch_rate,
            "total_score": result.total_score,
            "max_combo": result.max_combo,
            "typing_accuracy": result.typing_accuracy,
            "quiz_correct": result.quiz_correct,
            "quiz_total": result.quiz_total,
            "ai_summary": session.ai_summary,
            "completed_at": result.completed_at,
        })


class SessionSummaryView(APIView):
    """
    GET /api/sessions/{id}/summary/ — AI 정리본 조회
    이미 있으면 캐시 반환, 없으면 AI 서버에 요청 후 저장
    파일 세션은 complete 이벤트에서 summary 못 받으면 빈 문자열 반환
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        session = get_session_or_404(pk, request.user)
        if not session:
            return error_response("세션을 찾을 수 없습니다.", status=404)

        if session.ai_status != VideoSession.AI_DONE:
            return error_response("AI 처리가 완료되지 않았습니다.", status=400)

        # 이미 요약 있으면 캐시 반환
        if session.ai_summary:
            return success_response("AI 정리본 조회 성공", {
                "session_id": session.id,
                "ai_summary": session.ai_summary,
                "is_cached": True,
            })

        # 파일 세션은 source_url 없어서 AI 서버 요청 불가
        # complete 이벤트에서 summary 안 왔으면 빈 문자열 반환
        if session.source_type == VideoSession.SOURCE_FILE:
            return success_response("AI 정리본 조회 성공", {
                "session_id": session.id,
                "ai_summary": "",
                "is_cached": False,
            })

        # 유튜브 세션 → AI 서버에 요청
        try:
            with httpx.Client(timeout=settings.AI_SERVER_TIMEOUT) as client:
                response = client.post(
                    f"{settings.AI_SERVER_URL}/api/summary/",
                    json={"url": session.source_url, "language": "ko"},
                )
                response.raise_for_status()
                data = response.json()
                summary = data.get("summary") or data.get("ai_summary", "")

                # DB에 저장 (캐싱)
                session.ai_summary = summary
                session.save(update_fields=["ai_summary"])

                return success_response("AI 정리본 조회 성공", {
                    "session_id": session.id,
                    "ai_summary": summary,
                    "is_cached": False,
                })

        except Exception as e:
            return error_response(
                f"AI 정리본 생성에 실패했습니다: {str(e)}", status=500
            )
    
    
class SessionStreamView(APIView):
    """
    POST /api/sessions/stream/
    AI 서버에서 챕터별 스트리밍 데이터를 받아서 프론트에 SSE로 전달
    chapter_ready: Subtitle/BlankItem/FallEvent/Quiz DB 저장 후 quiz_id 추가
    complete: DB 저장 완료 후 ai_status → done
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        url = request.data.get("url")
        session_id = request.data.get("session_id")
        language = request.data.get("language", "ko")

        if not url:
            def error_stream():
                yield f"data: {json.dumps({'type': 'error', 'message': 'URL을 입력해주세요.'})}\n\n"
            return StreamingHttpResponse(
                error_stream(),
                content_type="text/event-stream",
                status=400,
            )

        session = None
        if session_id:
            session = get_session_or_404(session_id, request.user)

        def event_stream():
            try:
                if session:
                    session.ai_status = VideoSession.AI_PROCESSING
                    session.save(update_fields=["ai_status"])

                with httpx.Client(timeout=settings.AI_SERVER_TIMEOUT) as client:
                    with client.stream(
                        "POST",
                        f"{settings.AI_SERVER_URL}/api/process-url/stream",
                        json={"url": url, "language": language},
                        headers={"Content-Type": "application/json"},
                    ) as response:
                        response.raise_for_status()

                        for line in response.iter_lines():
                            if not line:
                                continue

                            if line.startswith("data: "):
                                raw = line[len("data: "):]
                            else:
                                raw = line

                            try:
                                chunk = json.loads(raw)
                            except json.JSONDecodeError:
                                yield f"{line}\n\n"
                                continue

                            # chapter_ready → Subtitle/BlankItem/FallEvent/Quiz DB 저장
                            if chunk.get("type") == "chapter_ready" and session:
                                from sessions.models import Subtitle, BlankItem, FallEvent
                                from quiz.models import Quiz

                                # ← segments → subtitles 로 변경!
                                segments = chunk.get("subtitles", [])
                                fall_events_data = chunk.get("fall_events", [])
                                quizzes = chunk.get("quizzes", [])

                                # 중복 방지: 기존 데이터 삭제 후 재생성
                                segment_ids = [s.get("segment_id") for s in segments]
                                Subtitle.objects.filter(
                                    session=session,
                                    segment_id__in=segment_ids
                                ).delete()

                                # Subtitle + BlankItem 저장
                                subtitle_map = {}
                                for s in segments:
                                    subtitle = Subtitle.objects.create(
                                        session=session,
                                        segment_id=s.get("segment_id", 0),
                                        start_sec=s.get("start", s.get("start_sec", 0.0)),
                                        end_sec=s.get("end", s.get("end_sec", 0.0)),
                                        original_text=s.get("original_text", ""),
                                        blank_text=s.get("blank_text", ""),
                                    )
                                    subtitle_map[s.get("segment_id")] = subtitle

                                    for b in s.get("blanks", []):
                                        BlankItem.objects.create(
                                            subtitle=subtitle,
                                            keyword=b.get("keyword", ""),
                                            position=b.get("position", 0),
                                            answer_length=b.get("answer_length", 0),
                                        )

                                # FallEvent 저장
                                fall_segment_ids = [fe.get("segment_id") for fe in fall_events_data]
                                FallEvent.objects.filter(
                                    session=session,
                                    subtitle__segment_id__in=fall_segment_ids
                                ).delete()

                                for fe in fall_events_data:
                                    seg_id = fe.get("segment_id")
                                    subtitle = subtitle_map.get(seg_id)
                                    if subtitle:
                                        FallEvent.objects.create(
                                            session=session,
                                            subtitle=subtitle,
                                            keyword=fe.get("keyword", ""),
                                            target_time=fe.get("target_time", 0.0),
                                            fall_window=fe.get("fall_window", 0.5),
                                        )

                                # Quiz 저장
                                new_quizzes = []
                                for q in quizzes:
                                    quiz_obj, _ = Quiz.objects.update_or_create(
                                        session=session,
                                        quiz_index=q.get("ai_quiz_index", q.get("quiz_id", 0)),
                                        defaults={
                                            "trigger_time": q.get("trigger_time", 0),
                                            "segment_start": q.get("segment_range", [0, 0])[0],
                                            "segment_end": q.get("segment_range", [0, 0])[1],
                                            "question": q.get("question", ""),
                                            "options_json": q.get("options", []),
                                            "answer_index": q.get("answer_index", 0),
                                            "explanation": q.get("explanation", ""),
                                        },
                                    )
                                    new_quizzes.append({
                                        "quiz_id": quiz_obj.id,
                                        "ai_quiz_index": q.get("ai_quiz_index", q.get("quiz_id", 0)),
                                        "trigger_time": q.get("trigger_time", 0),
                                        "segment_range": q.get("segment_range", [0, 0]),
                                        "question": q.get("question", ""),
                                        "options": q.get("options", []),
                                        "answer_index": q.get("answer_index", 0),
                                        "explanation": q.get("explanation", ""),
                                    })

                                chunk["quizzes"] = new_quizzes
                                yield f"data: {json.dumps(chunk)}\n\n"
                                continue

                            # complete → ai_summary 저장 + done 처리
                            if chunk.get("type") == "complete" and session:
                                summary = chunk.get("summary") or chunk.get("ai_summary")
                                if summary:
                                    session.ai_summary = summary
                                session.ai_status = VideoSession.AI_DONE
                                session.save(update_fields=["ai_status", "ai_summary"])

                            yield f"data: {json.dumps(chunk)}\n\n"

            except httpx.TimeoutException:
                if session:
                    session.ai_status = VideoSession.AI_FAILED
                    session.ai_error_message = "AI 서버 응답 시간이 초과되었습니다."
                    session.save(update_fields=["ai_status", "ai_error_message"])
                yield f"data: {json.dumps({'type': 'error', 'message': 'AI 서버 응답 시간이 초과되었습니다.'})}\n\n"

            except httpx.HTTPStatusError as e:
                if session:
                    session.ai_status = VideoSession.AI_FAILED
                    session.ai_error_message = f"AI 서버 오류: {e.response.status_code}"
                    session.save(update_fields=["ai_status", "ai_error_message"])
                yield f"data: {json.dumps({'type': 'error', 'message': f'AI 서버 오류: {e.response.status_code}'})}\n\n"

            except Exception as e:
                if session:
                    session.ai_status = VideoSession.AI_FAILED
                    session.ai_error_message = str(e)
                    session.save(update_fields=["ai_status", "ai_error_message"])
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
    
class VideoFileStreamView(APIView):
    """
    POST /api/sessions/stream/file/
    파일 업로드 → AI 서버로 전달 → SSE 스트리밍 반환
    chapter_ready: Subtitle/BlankItem/FallEvent/Quiz DB 저장 후 quiz_id 추가
    complete: DB 저장 완료 후 ai_status → done
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")
        session_id = request.data.get("session_id")
        language = request.data.get("language", "ko")

        if not file:
            def error_stream():
                yield f"data: {json.dumps({'type': 'error', 'message': '파일을 업로드해주세요.'})}\n\n"
            return StreamingHttpResponse(
                error_stream(),
                content_type="text/event-stream",
                status=400,
            )

        session = None
        if session_id:
            session = get_session_or_404(session_id, request.user)

        file_data = file.read()
        file_name = file.name
        file_content_type = file.content_type

        def event_stream():
            try:
                if session:
                    session.ai_status = VideoSession.AI_PROCESSING
                    session.save(update_fields=["ai_status"])

                with httpx.Client(timeout=settings.AI_SERVER_TIMEOUT) as client:
                    with client.stream(
                        "POST",
                        f"{settings.AI_SERVER_URL}/api/process/stream",
                        files={"file": (file_name, file_data, file_content_type)},
                        data={"language": language},
                    ) as response:
                        response.raise_for_status()

                        for line in response.iter_lines():
                            if not line:
                                continue

                            if line.startswith("data: "):
                                raw = line[len("data: "):]
                            else:
                                raw = line

                            try:
                                chunk = json.loads(raw)
                            except json.JSONDecodeError:
                                yield f"{line}\n\n"
                                continue
                            
                            # ── 디버그 로그 ──────────────────────────
                            print(f"[SSE chunk] type={chunk.get('type')} keys={list(chunk.keys())}", flush=True)
                            if chunk.get("type") == "complete":
                                print(f"[complete] {json.dumps(chunk, ensure_ascii=False)}", flush=True)
                            # ─────────────────────────────────────────

                            # chapter_ready → Subtitle/BlankItem/FallEvent/Quiz DB 저장
                            if chunk.get("type") == "chapter_ready" and session:
                                from sessions.models import Subtitle, BlankItem, FallEvent
                                from quiz.models import Quiz

                                # ← segments → subtitles 로 변경!
                                segments = chunk.get("subtitles", [])
                                fall_events_data = chunk.get("fall_events", [])
                                quizzes = chunk.get("quizzes", [])

                                # 중복 방지: 기존 데이터 삭제 후 재생성
                                segment_ids = [s.get("segment_id") for s in segments]
                                Subtitle.objects.filter(
                                    session=session,
                                    segment_id__in=segment_ids
                                ).delete()

                                # Subtitle + BlankItem 저장
                                subtitle_map = {}
                                for s in segments:
                                    subtitle = Subtitle.objects.create(
                                        session=session,
                                        segment_id=s.get("segment_id", 0),
                                        start_sec=s.get("start", s.get("start_sec", 0.0)),
                                        end_sec=s.get("end", s.get("end_sec", 0.0)),
                                        original_text=s.get("original_text", ""),
                                        blank_text=s.get("blank_text", ""),
                                    )
                                    subtitle_map[s.get("segment_id")] = subtitle

                                    for b in s.get("blanks", []):
                                        BlankItem.objects.create(
                                            subtitle=subtitle,
                                            keyword=b.get("keyword", ""),
                                            position=b.get("position", 0),
                                            answer_length=b.get("answer_length", 0),
                                        )

                                # FallEvent 저장
                                fall_segment_ids = [fe.get("segment_id") for fe in fall_events_data]
                                FallEvent.objects.filter(
                                    session=session,
                                    subtitle__segment_id__in=fall_segment_ids
                                ).delete()

                                for fe in fall_events_data:
                                    seg_id = fe.get("segment_id")
                                    subtitle = subtitle_map.get(seg_id)
                                    if subtitle:
                                        FallEvent.objects.create(
                                            session=session,
                                            subtitle=subtitle,
                                            keyword=fe.get("keyword", ""),
                                            target_time=fe.get("target_time", 0.0),
                                            fall_window=fe.get("fall_window", 0.5),
                                        )

                                # Quiz 저장
                                new_quizzes = []
                                for q in quizzes:
                                    quiz_obj, _ = Quiz.objects.update_or_create(
                                        session=session,
                                        quiz_index=q.get("ai_quiz_index", q.get("quiz_id", 0)),
                                        defaults={
                                            "trigger_time": q.get("trigger_time", 0),
                                            "segment_start": q.get("segment_range", [0, 0])[0],
                                            "segment_end": q.get("segment_range", [0, 0])[1],
                                            "question": q.get("question", ""),
                                            "options_json": q.get("options", []),
                                            "answer_index": q.get("answer_index", 0),
                                            "explanation": q.get("explanation", ""),
                                        },
                                    )
                                    new_quizzes.append({
                                        "quiz_id": quiz_obj.id,
                                        "ai_quiz_index": q.get("ai_quiz_index", q.get("quiz_id", 0)),
                                        "trigger_time": q.get("trigger_time", 0),
                                        "segment_range": q.get("segment_range", [0, 0]),
                                        "question": q.get("question", ""),
                                        "options": q.get("options", []),
                                        "answer_index": q.get("answer_index", 0),
                                        "explanation": q.get("explanation", ""),
                                    })

                                chunk["quizzes"] = new_quizzes
                                yield f"data: {json.dumps(chunk)}\n\n"
                                continue

                            # complete → ai_summary 저장 + done 처리
                            if chunk.get("type") == "complete" and session:
                                summary = chunk.get("summary") or chunk.get("ai_summary")
                                if summary:
                                    session.ai_summary = summary
                                session.ai_status = VideoSession.AI_DONE
                                session.save(update_fields=["ai_status", "ai_summary"])

                            yield f"data: {json.dumps(chunk)}\n\n"

            except httpx.TimeoutException:
                if session:
                    session.ai_status = VideoSession.AI_FAILED
                    session.ai_error_message = "AI 서버 응답 시간이 초과되었습니다."
                    session.save(update_fields=["ai_status", "ai_error_message"])
                yield f"data: {json.dumps({'type': 'error', 'message': 'AI 서버 응답 시간이 초과되었습니다.'})}\n\n"

            except httpx.HTTPStatusError as e:
                if session:
                    session.ai_status = VideoSession.AI_FAILED
                    session.ai_error_message = f"AI 서버 오류: {e.response.status_code}"
                    session.save(update_fields=["ai_status", "ai_error_message"])
                yield f"data: {json.dumps({'type': 'error', 'message': f'AI 서버 오류: {e.response.status_code}'})}\n\n"

            except Exception as e:
                if session:
                    session.ai_status = VideoSession.AI_FAILED
                    session.ai_error_message = str(e)
                    session.save(update_fields=["ai_status", "ai_error_message"])
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
    
class SessionFileResumeView(APIView):
    """
    POST /api/sessions/{id}/stream/resume/
    새로고침 후 sessionId만으로 로컬 파일 스트리밍 재개
    file_path가 서버에 저장되어 있으면 그걸로 AI 서버에 다시 요청
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        session = get_session_or_404(pk, request.user)
        if not session:
            return error_response("세션을 찾을 수 없습니다.", status=404)

        # 유튜브 URL 세션이면 stream/ 으로 재개 가능
        if session.source_type == VideoSession.SOURCE_YOUTUBE:
            return error_response(
                "유튜브 URL 세션은 /api/sessions/stream/ 으로 재개하세요.",
                {"source_url": session.source_url},
                status=400,
            )

        # 로컬 파일 세션인데 file_path 없으면
        if not session.file_path:
            return error_response("저장된 파일을 찾을 수 없습니다.", status=404)

        import os
        from django.conf import settings as django_settings

        # file_path = "/media/videos/1_lecture.mp4" → 실제 파일 경로로 변환
        relative_path = session.file_path.lstrip("/")
        relative_path = relative_path.replace("media/", "", 1)
        full_path = os.path.join(django_settings.MEDIA_ROOT, relative_path)

        if not os.path.exists(full_path):
            return error_response("서버에 파일이 존재하지 않습니다.", status=404)

        language = request.data.get("language", "ko")
        file_size = os.path.getsize(full_path)

        def event_stream():
            try:
                # 파일 전체를 메모리에 올리지 않고 스트림으로 직접 전달
                with open(full_path, "rb") as f:
                    with httpx.Client(timeout=django_settings.AI_SERVER_TIMEOUT) as client:
                        with client.stream(
                            "POST",
                            f"{django_settings.AI_SERVER_URL}/api/process/stream",
                            content=f,
                            headers={
                                "Content-Type": "video/mp4",
                                "Content-Length": str(file_size),
                            },
                            params={"language": language},
                        ) as response:
                            response.raise_for_status()
                            for line in response.iter_lines():
                                if line:
                                    yield f"{line}\n\n"

            except httpx.TimeoutException:
                yield f"data: {json.dumps({'type': 'error', 'message': 'AI 서버 응답 시간이 초과되었습니다.'})}\n\n"

            except httpx.HTTPStatusError as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'AI 서버 오류: {e.response.status_code}'})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
    
class SessionVideoView(APIView):
    """
    GET /api/sessions/{id}/video/
    로컬 파일 세션의 영상을 HTTP로 서빙
    Range 요청 지원 → 영상 seek 가능
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        import os
        import mimetypes
        from django.conf import settings as django_settings

        session = get_session_or_404(pk, request.user)
        if not session:
            return error_response("세션을 찾을 수 없습니다.", status=404)

        if not session.file_path:
            return error_response("저장된 파일이 없습니다.", status=404)

        relative_path = session.file_path.lstrip("/")
        relative_path = relative_path.replace("media/", "", 1)
        full_path = os.path.join(django_settings.MEDIA_ROOT, relative_path)

        if not os.path.exists(full_path):
            return error_response("파일을 찾을 수 없습니다.", status=404)

        content_type, _ = mimetypes.guess_type(full_path)
        content_type = content_type or "video/mp4"
        file_size = os.path.getsize(full_path)

        range_header = request.META.get("HTTP_RANGE", "").strip()

        if range_header:
            range_match = range_header.replace("bytes=", "").split("-")
            start = int(range_match[0])
            end = int(range_match[1]) if range_match[1] else file_size - 1
            length = end - start + 1

            with open(full_path, "rb") as f:
                f.seek(start)
                data = f.read(length)

            response = HttpResponse(data, status=206, content_type=content_type)
            response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            response["Accept-Ranges"] = "bytes"
            response["Content-Length"] = str(length)
            return response

        from django.http import FileResponse
        response = FileResponse(
            open(full_path, "rb"),
            content_type=content_type,
        )
        response["Accept-Ranges"] = "bytes"
        response["Content-Length"] = str(file_size)
        return response