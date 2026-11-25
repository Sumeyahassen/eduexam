from rest_framework import generics, viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from academics.models import Student
from exams.models import Exam
from grading.models import ExamAttempt

from .models import Institution, User
from .permissions import IsSuperAdmin, IsInstAdmin
from .serializers import (
    EduExamTokenSerializer,
    InstitutionSerializer,
    RegisterUserSerializer,
    UserSerializer,
)


class LoginView(TokenObtainPairView):
    serializer_class = EduExamTokenSerializer
    permission_classes = [AllowAny]


class RegisterUserView(generics.CreateAPIView):
    serializer_class = RegisterUserSerializer
    permission_classes = [IsInstAdmin]

    def perform_create(self, serializer):
        inst = getattr(self.request, "institution", None) or self.request.user.institution
        serializer.save(institution=inst)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class InstitutionViewSet(viewsets.ModelViewSet):
    serializer_class = InstitutionSerializer
    permission_classes = [IsSuperAdmin]
    queryset = Institution.objects.all()
    lookup_field = "slug"


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsInstAdmin]

    def get_queryset(self):
        inst = getattr(self.request, "institution", None) or self.request.user.institution
        qs = User.objects.filter(institution=inst)
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        return qs

    def perform_create(self, serializer):
        inst = getattr(self.request, "institution", None) or self.request.user.institution
        serializer.save(institution=inst)


class PlatformStatsView(APIView):
    """
    GET /api/v1/stats/
    Super Admin only — platform-wide statistics.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        institutions = Institution.objects.all()
        total = institutions.count()
        active = institutions.filter(is_active=True).count()
        k12 = institutions.filter(type=Institution.Type.K12_SCHOOL).count()
        higher = institutions.filter(type=Institution.Type.HIGHER_ED).count()

        total_examiners = User.objects.filter(role=User.Role.EXAMINER).count()
        total_students  = Student.objects.count()
        total_exams     = Exam.objects.count()
        total_attempts  = ExamAttempt.objects.count()

        inst_data = []
        for inst in institutions:
            inst_data.append({
                "id":        str(inst.id),
                "name":      inst.name,
                "slug":      inst.slug,
                "type":      inst.type,
                "is_active": inst.is_active,
                "contact":   inst.contact,
                "created_at": inst.created_at.isoformat(),
                "examiners": User.objects.filter(
                    institution=inst, role=User.Role.EXAMINER).count(),
                "students":  Student.objects.filter(institution=inst).count(),
                "exams":     Exam.objects.filter(institution=inst).count(),
                "attempts":  ExamAttempt.objects.filter(
                    exam__institution=inst).count(),
            })

        return Response({
            "total_institutions":  total,
            "active_institutions": active,
            "k12_count":           k12,
            "higher_ed_count":     higher,
            "total_examiners":     total_examiners,
            "total_students":      total_students,
            "total_exams":         total_exams,
            "total_attempts":      total_attempts,
            "institutions":        inst_data,
        })
