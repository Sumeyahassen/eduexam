from django.core.cache import cache
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from tenants.permissions import IsExaminer, IsStudent
from tenants.mixins import TenantScopeMixin
from academics.models import Student
from exams.models import Exam, Question
from .models import ExamAttempt, StudentAnswer
from .serializers import (
    ExamAttemptSerializer,
    SubmitExamSerializer,
    AutoSaveSerializer,
    ManualScoreSerializer,
)
from .services import auto_grade_attempt, finalize_manual_review


def _get_institution(request):
    inst = getattr(request, "institution", None)
    if not inst and request.user.is_authenticated:
        inst = getattr(request.user, "institution", None)
    return inst


def _get_student(request):
    """Resolve the Student record for the authenticated student user."""
    institution = _get_institution(request)
    if not institution:
        return None
    try:
        return Student.objects.get(
            institution=institution,
            student_id=request.user.username,
        )
    except Student.DoesNotExist:
        return None


# ── Student-facing views ────────────────────────────────────────────────────

class AttemptViewSet(viewsets.GenericViewSet):
    permission_classes = [IsStudent]
    serializer_class = ExamAttemptSerializer

    def create(self, request):
        """POST /api/v1/attempts/ — start or resume an attempt."""
        exam_id = request.data.get("exam")
        try:
            exam = Exam.objects.get(
                pk=exam_id,
                institution=_get_institution(request),
                is_published=True,
            )
        except Exam.DoesNotExist:
            return Response({"detail": "Exam not found."}, status=404)

        student = _get_student(request)
        if not student:
            return Response(
                {"detail": "Student record not found for this user."},
                status=status.HTTP_403_FORBIDDEN,
            )

        attempt, created = ExamAttempt.objects.get_or_create(
            exam=exam,
            student=student,
            defaults={"status": ExamAttempt.Status.IN_PROGRESS},
        )

        if not created and attempt.status != ExamAttempt.Status.IN_PROGRESS:
            return Response(
                {"detail": "Exam already submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ExamAttemptSerializer(attempt)
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=code)

    @action(detail=True, methods=["post"], url_path="autosave")
    def autosave(self, request, pk=None):
        """POST /api/v1/attempts/{id}/autosave/"""
        student = _get_student(request)
        attempt = ExamAttempt.objects.get(pk=pk, student=student)
        serializer = AutoSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cache_key = f"autosave:{attempt.pk}"
        cache.set(cache_key, serializer.validated_data["answers"], timeout=3600)
        self._persist_answers(attempt, serializer.validated_data["answers"])
        return Response({"saved": True})

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        """POST /api/v1/attempts/{id}/submit/"""
        student = _get_student(request)
        attempt = ExamAttempt.objects.get(pk=pk, student=student)

        if attempt.status != ExamAttempt.Status.IN_PROGRESS:
            return Response(
                {"detail": "Attempt already submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubmitExamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self._persist_answers(attempt, serializer.validated_data["answers"])
        auto_grade_attempt(attempt)
        return Response(ExamAttemptSerializer(attempt).data)

    @action(detail=False, methods=["get"], url_path="my-results")
    def my_results(self, request):
        """
        GET /api/v1/attempts/my-results/
        Returns all FINALIZED attempts for the current student with full detail.
        """
        student = _get_student(request)
        if not student:
            return Response(
                {"detail": "Student record not found."},
                status=status.HTTP_403_FORBIDDEN,
            )

        attempts = (
            ExamAttempt.objects.filter(
                student=student,
                status=ExamAttempt.Status.FINALIZED,
            )
            .select_related("exam__subject")
            .prefetch_related("answers__question")
            .order_by("-submitted_at")
        )

        results = []
        for attempt in attempts:
            total_possible = sum(
                q.points for q in attempt.exam.questions.all()
            )
            answers_detail = []
            for ans in attempt.answers.all():
                answers_detail.append({
                    "question_prompt": ans.question.prompt,
                    "question_type":   ans.question.type,
                    "response_data":   ans.response_data,
                    "points_awarded":  ans.points_awarded,
                    "max_points":      ans.question.points,
                    "feedback":        ans.feedback,
                })

            results.append({
                "attempt_id":     str(attempt.id),
                "exam_title":     attempt.exam.title,
                "subject_name":   attempt.exam.subject.name,
                "level_or_dept":  attempt.exam.subject.level_or_dept,
                "submitted_at":   attempt.submitted_at,
                "auto_score":     attempt.auto_score,
                "manual_score":   attempt.manual_score,
                "final_score":    attempt.final_score,
                "total_possible": total_possible,
                "answers":        answers_detail,
            })

        return Response(results)

    def _persist_answers(self, attempt, answers):
        for item in answers:
            try:
                question = Question.objects.get(pk=item["question"], exam=attempt.exam)
            except Question.DoesNotExist:
                continue
            StudentAnswer.objects.update_or_create(
                attempt=attempt,
                question=question,
                defaults={"response_data": item.get("response_data", {})},
            )


# ── Examiner-facing views ───────────────────────────────────────────────────

class ReviewQueueViewSet(viewsets.GenericViewSet):
    permission_classes = [IsExaminer]
    serializer_class = ExamAttemptSerializer

    def list(self, request):
        """GET /api/v1/review/ — pending manual review."""
        attempts = (
            ExamAttempt.objects.filter(
                exam__institution=_get_institution(request),
                status=ExamAttempt.Status.NEEDS_MANUAL,
            )
            .select_related("exam__subject", "student")
            .prefetch_related("answers__question")
        )
        data = []
        for a in attempts:
            data.append({
                "id":          str(a.id),
                "exam":        str(a.exam.id),
                "exam_title":  a.exam.title,
                "subject":     a.exam.subject.name,
                "student_id":  a.student.student_id,
                "student_name": a.student.full_name,
                "auto_score":  a.auto_score,
                "submitted_at": a.submitted_at,
            })
        return Response(data)

    def retrieve(self, request, pk=None):
        attempt = ExamAttempt.objects.get(
            pk=pk, exam__institution=_get_institution(request)
        )
        return Response(ExamAttemptSerializer(attempt).data)

    @action(detail=True, methods=["post"], url_path="score")
    def score(self, request, pk=None):
        """
        POST /api/v1/review/{id}/score/
        {"scores": [{answer_id, points_awarded, feedback}]}
        """
        attempt = ExamAttempt.objects.get(
            pk=pk, exam__institution=_get_institution(request)
        )
        serializer = ManualScoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for item in serializer.validated_data["scores"]:
            StudentAnswer.objects.filter(
                pk=item["answer_id"], attempt=attempt
            ).update(
                points_awarded=item["points_awarded"],
                feedback=item.get("feedback", ""),
                reviewed=True,
            )

        finalize_manual_review(attempt)
        return Response(ExamAttemptSerializer(attempt).data)

    @action(detail=False, methods=["get"], url_path="results")
    def results(self, request):
        """GET /api/v1/review/results/ — all finalized attempts."""
        attempts = (
            ExamAttempt.objects.filter(
                exam__institution=_get_institution(request),
                status=ExamAttempt.Status.FINALIZED,
            )
            .select_related("exam", "student")
        )
        return Response(ExamAttemptSerializer(attempts, many=True).data)
