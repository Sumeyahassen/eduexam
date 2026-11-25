import uuid
from django.db import models
from tenants.models import Institution


class AcademicYear(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE,
                                    related_name="academic_years")
    label       = models.CharField(max_length=50)   # e.g. "2024-2025"
    is_active   = models.BooleanField(default=True)

    class Meta:
        unique_together = ("institution", "label")
        ordering = ["-label"]

    def __str__(self):
        return f"{self.institution.slug} / {self.label}"


class SubjectOrCourse(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution   = models.ForeignKey(Institution, on_delete=models.CASCADE,
                                      related_name="subjects")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE,
                                      related_name="subjects")
    name          = models.CharField(max_length=255)
    code          = models.CharField(max_length=50, blank=True)
    # Flexible field: "Grade 7" for K-12 or "Computer Science Dept" for university
    level_or_dept = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.level_or_dept})"


class Student(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE,
                                    related_name="students")
    student_id  = models.CharField(max_length=50)   # institutional student number
    full_name   = models.CharField(max_length=255)
    enrollments = models.ManyToManyField(SubjectOrCourse, blank=True,
                                         related_name="students")
    access_pin  = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ("institution", "student_id")

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"
