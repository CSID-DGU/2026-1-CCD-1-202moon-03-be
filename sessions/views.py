import json
import httpx
from django.http import StreamingHttpResponse
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

            # 지금은 media/ 폴더에 저장 (나중에 S3로 교체)
            import os
            from django.conf import settings as django_settings

            save_dir = os.path.join(django_settings.MEDIA_ROOT, "videos")
            os.makedirs(save_dir, exist_ok=True)

            file_name = f"{request.user.id}_{file.name}"
            file_full_path = os.path.join(save_dir, file_name)

            with open(file_full_path, "wb") as f:
                for chunk in file.chunks():
                    f.write(chunk)

            # 프론트에서 접근 가능한 URL로 변환
            file_path = f"{django_settings.MEDIA_URL}videos/{file_name}"

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
    이미 있으면 캐시 반환, 없으면 AI 서버 요청
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        session = get_session_or_404(pk, request.user)
        if not session:
            return error_response("세션을 찾을 수 없습니다.", status=404)

        if session.ai_status != VideoSession.AI_DONE:
            return error_response("AI 처리가 완료되지 않았습니다.", status=400)

        # 이미 요약 있으면 바로 반환 (캐시)
        if session.ai_summary:
            return success_response("AI 정리본 조회 성공", {
                "session_id": session.id,
                "ai_summary": session.ai_summary,
                "is_cached": True,
            })

        # TODO: AI 서버에 요약 요청 후 저장 (추후 구현)
        return error_response("AI 정리본을 아직 생성할 수 없습니다.", status=400)
    
    
class SessionStreamView(APIView):
    """
    POST /api/sessions/stream/
    AI 서버에서 챕터별 스트리밍 데이터를 받아서 프론트에 SSE로 전달
    
    쉽게 말하면:
    프론트 → DRF → AI서버 → DRF → 프론트
    DRF가 중간에서 그냥 전달해주는 역할
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        url = request.data.get("url")
        language = request.data.get("language", "ko")

        if not url:
            # SSE는 일반 에러 응답 못 쓰니까 에러도 SSE 형식으로
            def error_stream():
                yield f"data: {json.dumps({'type': 'error', 'message': 'URL을 입력해주세요.'})}\n\n"
            return StreamingHttpResponse(
                error_stream(),
                content_type="text/event-stream",
                status=400,
            )

        def event_stream():
            """
            AI 서버에서 받은 SSE 스트림을 그대로 프론트에 전달
            """
            try:
                with httpx.Client(timeout=settings.AI_SERVER_TIMEOUT) as client:
                    # AI 서버에 스트리밍 요청
                    with client.stream(
                        "POST",
                        f"{settings.AI_SERVER_URL}/api/process-url/stream",
                        json={"url": url, "language": language},
                        headers={"Content-Type": "application/json"},
                    ) as response:
                        response.raise_for_status()

                        # AI 서버에서 오는 데이터를 그대로 프론트로 전달
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
        # SSE 필수 헤더
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"  # Nginx 버퍼링 방지
        return response


class VideoFileStreamView(APIView):
    """
    POST /api/sessions/stream/file/
    파일 업로드 → AI 서버로 전달 → SSE 스트리밍 반환
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")
        language = request.data.get("language", "ko")

        if not file:
            def error_stream():
                yield f"data: {json.dumps({'type': 'error', 'message': '파일을 업로드해주세요.'})}\n\n"
            return StreamingHttpResponse(
                error_stream(),
                content_type="text/event-stream",
                status=400,
            )

        def event_stream():
            try:
                with httpx.Client(timeout=settings.AI_SERVER_TIMEOUT) as client:
                    with client.stream(
                        "POST",
                        f"{settings.AI_SERVER_URL}/api/process/stream",
                        files={"file": (file.name, file.read(), file.content_type)},
                        data={"language": language},
                    ) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if line:
                                yield f"{line}\n\n"

            except Exception as e:
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