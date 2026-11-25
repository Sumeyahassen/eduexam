import uuid
from django.db import models
from exams.models import Exam, Question
from academics.models import Student


class ExamAttempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS  = "IN_PROGRESS",  "In Progress"
        NEEDS_MANUAL = "NEEDS_MANUAL", "Needs Manual Review"
        FINALIZED    = "FINALIZED",    "Finalized"

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam         = models.ForeignKey(Exam, on_delete=models.CASCADE,
                                     related_name="attempts")
    student      = models.ForeignKey(Student, on_delete=models.CASCADE,
                                     related_name="attempts")
    status       = models.CharField(max_length=20, choices=Status.choices,
                                    default=Status.IN_PROGRESS)
    auto_score   = models.FloatField(null=True, blank=True)
    manual_score = models.FloatField(null=True, blank=True)
    final_score  = models.FloatField(null=True, blank=True)
    started_at   = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("exam", "student")

    def __str__(self):
        return f"{self.student} → {self.exam} [{self.status}]"


class StudentAnswer(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt        = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE,
                                       related_name="answers")
    question       = models.ForeignKey(Question, on_delete=models.CASCADE)
    # response_data structure matches question type:
    #   MCQ/TF:  {"selected": "A"}
    #   MATCH:   {"pairs": [["left1","right1"], ...]}
    #   FILL:    {"blanks": ["ans1", "ans2"]}
    #   SA:      {"text": "student's written answer"}
    response_data  = models.JSONField(default=dict)
    points_awarded = models.FloatField(null=True, blank=True)
    reviewed       = models.BooleanField(default=False)
    feedback       = models.TextField(blank=True)

    class Meta:
        unique_together = ("attempt", "question")

    def __str__(self):
        return f"Answer by {self.attempt.student} for Q:{self.question_id}"
