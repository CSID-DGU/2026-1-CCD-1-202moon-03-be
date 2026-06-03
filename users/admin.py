from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserSetting


class UserSettingInline(admin.StackedInline):
    model = UserSetting
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["id", "username", "email", "nickname", "avatar_type", "is_staff", "created_at"]
    search_fields = ["username", "email", "nickname"]
    list_filter = ["is_staff", "is_active", "avatar_type"]
    inlines = [UserSettingInline]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("추가 정보", {"fields": ("nickname", "avatar_type", "birth_date", "gender", "stimulation_level", "is_tutorial_done")}),
    )