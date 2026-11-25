from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from tenants.views import (
    LoginView, RegisterUserView, MeView,
    InstitutionViewSet, UserViewSet, PlatformStatsView,
)
from academics.views import AcademicYearViewSet, SubjectOrCourseViewSet, StudentViewSet
from exams.views import ExamViewSet, StudentExamViewSet, QuestionViewSet
from grading.views import AttemptViewSet, ReviewQueueViewSet

router = DefaultRouter()
router.register("institutions",   InstitutionViewSet,     basename="institution")
router.register("users",          UserViewSet,            basename="user")
router.register("academic-years", AcademicYearViewSet,    basename="academic-year")
router.register("subjects",       SubjectOrCourseViewSet, basename="subject")
router.register("students",       StudentViewSet,         basename="student")
router.register("exams",          ExamViewSet,            basename="exam")
router.register("student-exams",  StudentExamViewSet,     basename="student-exam")
router.register("attempts",       AttemptViewSet,         basename="attempt")
router.register("review",         ReviewQueueViewSet,     basename="review")

# Nested: /exams/{exam_pk}/questions/
exam_router = nested_routers.NestedDefaultRouter(router, "exams", lookup="exam")
exam_router.register("questions", QuestionViewSet, basename="exam-question")

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth
    path("api/v1/auth/login/",    LoginView.as_view(),         name="token_obtain"),
    path("api/v1/auth/refresh/",  TokenRefreshView.as_view(),  name="token_refresh"),
    path("api/v1/auth/register/", RegisterUserView.as_view(),  name="register"),
    path("api/v1/auth/me/",       MeView.as_view(),            name="me"),

    # Platform stats (super admin)
    path("api/v1/stats/", PlatformStatsView.as_view(), name="platform-stats"),

    # API
    path("api/v1/", include(router.urls)),
    path("api/v1/", include(exam_router.urls)),

    # Docs
    path("api/schema/", SpectacularAPIView.as_view(),                        name="schema"),
    path("api/docs/",   SpectacularSwaggerView.as_view(url_name="schema"),   name="swagger-ui"),
]
