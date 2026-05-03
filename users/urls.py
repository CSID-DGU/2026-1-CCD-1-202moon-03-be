from django.urls import path
from . import views

urlpatterns = [
    path("me/", views.UserProfileView.as_view(), name="user-profile"),
    path("me/password/", views.PasswordChangeView.as_view(), name="password-change"),
    path("me/settings/", views.UserSettingView.as_view(), name="user-settings"),
    path("me/history/", views.LearningHistoryView.as_view(), name="learning-history"),
]