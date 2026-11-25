import uuid
from django.db import models
from tenants.models import Institution
from academics.models import SubjectOrCourse


class Exam(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution  = models.ForeignKey(Institution, on_delete=models.CASCADE,
                                     related_name="exams")
    subject      = models.ForeignKey(SubjectOrCourse, on_delete=models.CASCADE,
                                     related_name="exams")
    title        = models.CharField(max_length=255)
    duration_min = models.PositiveIntegerField()
    # Set to True automatically when a Short Answer question is added
    has_short_ans  = models.BooleanField(default=False)
    is_published   = models.BooleanField(default=False)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} — {self.subject}"


class Question(models.Model):
    class Type(models.TextChoices):
        MCQ          = "MCQ",   "Multiple Choice"
        TRUE_FALSE   = "TF",    "True / False"
        MATCHING     = "MATCH", "Matching"
        FILL_BLANK   = "FILL",  "Fill in the Blank"
        SHORT_ANSWER = "SA",    "Short Answer"

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam       = models.ForeignKey(Exam, on_delete=models.CASCADE,
                                   related_name="questions")
    type       = models.CharField(max_length=10, choices=Type.choices)
    prompt     = models.TextField()
    # answer_key structure differs per type:
    #   MCQ/TF:   {"correct": "A"}
    #   MATCH:    {"pairs": [["left1","right1"], ...]}
    #   FILL:     {"blanks": ["answer1", "answer2"]}
    #   SA:       {"model_answer": "...", "grading_notes": "..."}
    answer_key = models.JSONField()
    points     = models.FloatField()
    order      = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Keep has_short_ans flag on Exam in sync
        if self.type == self.Type.SHORT_ANSWER:
            Exam.objects.filter(pk=self.exam_id).update(has_short_ans=True)

    def __str__(self):
        return f"[{self.type}] {self.prompt[:60]}"
