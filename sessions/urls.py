from django.urls import path
from . import views
from game import views as game_views
from quiz import views as quiz_views

urlpatterns = [
    path("", views.SessionListCreateView.as_view(), name="session-list-create"),
    path("<int:pk>/", views.SessionDetailView.as_view(), name="session-detail"),
    path("<int:pk>/status/", views.SessionStatusView.as_view(), name="session-status"),
    path("<int:pk>/game/start/", game_views.GameStartView.as_view(), name="game-start"),
    path("<int:pk>/game/end/", game_views.GameEndView.as_view(), name="game-end"),
    path("<int:pk>/quiz/retry/", quiz_views.QuizRetryView.as_view(), name="quiz-retry"),
    path("<int:pk>/quiz/<int:qid>/answer/", quiz_views.QuizAnswerView.as_view(), name="quiz-answer"),
    path("<int:pk>/result/", views.SessionResultView.as_view(), name="session-result"),
    path("<int:pk>/summary/", views.SessionSummaryView.as_view(), name="session-summary"),
    path("stream/", views.SessionStreamView.as_view(), name="session-stream"),
    path("stream/file/", views.VideoFileStreamView.as_view(), name="session-stream-file"),
    path("stream/s3/", views.S3VideoStreamView.as_view(), name="session-stream-s3"),
    path("presigned-url/", views.S3PresignedURLView.as_view(), name="session-presigned-url"),
    path("<int:pk>/stream/resume/", views.SessionFileResumeView.as_view(), name="session-stream-resume"),
    path("<int:pk>/video/", views.SessionVideoView.as_view(), name="session-video"),
]