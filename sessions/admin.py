from django.contrib import admin
from .models import VideoSession, Subtitle, BlankItem, FallEvent


class BlankItemInline(admin.TabularInline):
    model = BlankItem
    extra = 0


class SubtitleInline(admin.TabularInline):
    model = Subtitle
    extra = 0
    show_change_link = True


class FallEventInline(admin.TabularInline):
    model = FallEvent
    extra = 0


@admin.register(VideoSession)
class VideoSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "title", "source_type", "mode", "ai_status", "created_at"]
    list_filter = ["source_type", "mode", "ai_status"]
    search_fields = ["title", "user__username"]
    inlines = [SubtitleInline, FallEventInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Subtitle)
class SubtitleAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "segment_id", "start_sec", "end_sec", "original_text"]
    search_fields = ["session__title", "original_text"]
    inlines = [BlankItemInline]


@admin.register(BlankItem)
class BlankItemAdmin(admin.ModelAdmin):
    list_display = ["id", "subtitle", "keyword", "position", "answer_length"]


@admin.register(FallEvent)
class FallEventAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "keyword", "target_time", "fall_window"]
    search_fields = ["session__title", "keyword"]