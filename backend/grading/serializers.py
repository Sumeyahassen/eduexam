from django.db.models import Sum
from rest_framework import serializers
from .models import ExamAttempt, StudentAnswer


class StudentAnswerSerializer(serializers.ModelSerializer):
    question_prompt = serializers.CharField(source="question.prompt", read_only=True)
    question_type   = serializers.CharField(source="question.type",   read_only=True)
    max_points      = serializers.FloatField(source="question.points", read_only=True)

    class Meta:
        model = StudentAnswer
        fields = ["id", "question", "question_prompt", "question_type",
                  "response_data", "points_awarded", "reviewed",
                  "feedback", "max_points"]
        read_only_fields = ["id", "question_prompt", "question_type", "max_points"]


class ExamAttemptSerializer(serializers.ModelSerializer):
    answers = StudentAnswerSerializer(many=True, read_only=True)
    exam_title = serializers.CharField(source="exam.title", read_only=True)
    subject_name = serializers.CharField(source="exam.subject.name", read_only=True)
    total_points = serializers.SerializerMethodField()

    class Meta:
        model = ExamAttempt
        fields = ["id", "exam", "exam_title", "subject_name", "student", "status",
                  "auto_score", "manual_score", "final_score", "total_points",
                  "started_at", "submitted_at", "answers"]
        read_only_fields = ["id", "status", "auto_score", "manual_score",
                            "final_score", "started_at", "submitted_at",
                            "exam_title", "subject_name", "total_points"]

    def get_total_points(self, obj):
        result = obj.exam.questions.aggregate(total=Sum("points"))
        return result["total"] or 0


class SubmitExamSerializer(serializers.Serializer):
    """
    Payload the student sends when submitting an exam.
    answers: list of {question: <uuid>, response_data: {...}}
    """
    answers = serializers.ListField(
        child=serializers.DictField(), allow_empty=False
    )


class AutoSaveSerializer(serializers.Serializer):
    """Periodic auto-save payload — partial answers are fine."""
    answers = serializers.ListField(
        child=serializers.DictField(), allow_empty=True
    )


class ManualScoreSerializer(serializers.Serializer):
    """
    Examiner submits scores for all Short Answer questions in one request.
    scores: list of {answer_id: <uuid>, points_awarded: float, feedback: str}
    """
    scores = serializers.ListField(child=serializers.DictField(), allow_empty=False)
