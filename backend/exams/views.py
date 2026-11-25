from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from tenants.permissions import IsExaminer, IsStudent
from tenants.mixins import TenantScopeMixin
from .models import Exam, Question
from .serializers import ExamSerializer, ExamListSerializer, QuestionSerializer


class ExamViewSet(TenantScopeMixin, viewsets.ModelViewSet):
    permission_classes = [IsExaminer]

    def get_serializer_class(self):
        return ExamListSerializer if self.action == "list" else ExamSerializer

    def get_queryset(self):
        return (
            Exam.objects.filter(institution=self.get_institution())
            .select_related("subject")
            .prefetch_related("questions")
        )

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        exam = self.get_object()
        exam.is_published = True
        exam.save(update_fields=["is_published"])
        return Response({"status": "published"})

    @action(detail=True, methods=["post"], url_path="unpublish")
    def unpublish(self, request, pk=None):
        exam = self.get_object()
        exam.is_published = False
        exam.save(update_fields=["is_published"])
        return Response({"status": "unpublished"})


class StudentExamViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExamSerializer
    permission_classes = [IsStudent]

    def get_queryset(self):
        institution = getattr(self.request, "institution", None)
        if not institution and self.request.user.is_authenticated:
            institution = getattr(self.request.user, "institution", None)
        if not institution:
            return Exam.objects.none()

        student = getattr(self.request, "student", None)
        if not student:
            return Exam.objects.none()

        enrolled_subjects = student.enrollments.values_list("id", flat=True)
        return (
            Exam.objects.filter(
                institution=institution,
                is_published=True,
                subject__in=enrolled_subjects,
            )
            .select_related("subject")
            .prefetch_related("questions")
        )


class QuestionViewSet(TenantScopeMixin, viewsets.ModelViewSet):
    serializer_class = QuestionSerializer
    permission_classes = [IsExaminer]

    def get_queryset(self):
        return Question.objects.filter(
            exam__institution=self.get_institution(),
            exam_id=self.kwargs["exam_pk"],
        )

    def perform_create(self, serializer):
        exam = Exam.objects.get(
            pk=self.kwargs["exam_pk"],
            institution=self.get_institution(),
        )
        serializer.save(exam=exam)
