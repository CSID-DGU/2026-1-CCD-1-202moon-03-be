from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("token/refresh/", views.TokenRefreshView.as_view(), name="token-refresh"),
    path("password/reset-request/", views.PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password/reset-confirm/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("survey/", views.SurveyView.as_view(), name="survey"),
]