from django.db import models
from django.conf import settings


class VideoSession(models.Model):
    SOURCE_YOUTUBE = "youtube_url"
    SOURCE_FILE = "file"
    SOURCE_PRIVATE = "private_url"
    SOURCE_CHOICES = [
        (SOURCE_YOUTUBE, "YouTube URL"),
        (SOURCE_FILE, "파일 업로드"),
        (SOURCE_PRIVATE, "개인 링크"),
    ]

    MODE_FIDGET = "fidget"
    MODE_RAIN = "rain"
    MODE_CHOICES = [
        (MODE_FIDGET, "피젯스피너 모드"),
        (MODE_RAIN, "집중호우 모드"),
    ]

    AI_PENDING = "pending"
    AI_PROCESSING = "processing"
    AI_DONE = "done"
    AI_FAILED = "failed"
    AI_STATUS_CHOICES = [
        (AI_PENDING, "대기"),
        (AI_PROCESSING, "처리 중"),
        (AI_DONE, "완료"),
        (AI_FAILED, "실패"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions"
    )
    title = models.CharField(max_length=200)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    source_url = models.URLField(null=True, blank=True)
    file_path = models.CharField(max_length=500, null=True, blank=True)
    thumbnail_url = models.URLField(null=True, blank=True)
    duration_sec = models.FloatField(null=True, blank=True)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    ai_status = models.CharField(
        max_length=20, choices=AI_STATUS_CHOICES, default=AI_PENDING
    )
    ai_error_message = models.TextField(null=True, blank=True)
    ai_summary = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "video_session"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class Subtitle(models.Model):
    session = models.ForeignKey(
        VideoSession, on_delete=models.CASCADE, related_name="subtitles"
    )
    segment_id = models.IntegerField()
    start_sec = models.FloatField()
    end_sec = models.FloatField()
    original_text = models.TextField()
    blank_text = models.TextField()

    class Meta:
        db_table = "subtitle"
        ordering = ["segment_id"]


class BlankItem(models.Model):
    subtitle = models.ForeignKey(
        Subtitle, on_delete=models.CASCADE, related_name="blanks"
    )
    keyword = models.CharField(max_length=100)
    position = models.IntegerField()
    answer_length = models.IntegerField()

    class Meta:
        db_table = "blank_item"


class FallEvent(models.Model):
    session = models.ForeignKey(
        VideoSession, on_delete=models.CASCADE, related_name="fall_events"
    )
    subtitle = models.ForeignKey(
        Subtitle, on_delete=models.CASCADE, related_name="fall_events"
    )
    keyword = models.CharField(max_length=100)
    target_time = models.FloatField()
    fall_window = models.FloatField()

    class Meta:
        db_table = "fall_event"
        ordering = ["target_time"]