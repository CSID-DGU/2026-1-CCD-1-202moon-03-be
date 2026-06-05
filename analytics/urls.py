from django.urls import path
from . import views

urlpatterns = [
    path("sessions/<int:pk>/result/", views.LearningResultDetailView.as_view(), name="learning-result-detail"),
    path("dashboard/", views.LearningDashboardView.as_view(), name="learning-dashboard"),
]