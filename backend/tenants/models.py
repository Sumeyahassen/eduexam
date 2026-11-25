import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class Institution(models.Model):
    class Type(models.TextChoices):
        K12_SCHOOL = "K12_SCHOOL", "K-12 School"
        HIGHER_ED  = "HIGHER_ED",  "College / University"

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=255)
    type       = models.CharField(max_length=20, choices=Type.choices)
    slug       = models.SlugField(unique=True)   # used as subdomain / URL prefix
    contact    = models.EmailField()
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.type})"


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Platform Super Admin"
        INST_ADMIN  = "INST_ADMIN",  "Institution Admin"
        EXAMINER    = "EXAMINER",    "Examiner / Instructor"
        STUDENT     = "STUDENT",     "Student"

    institution = models.ForeignKey(
        Institution, null=True, blank=True, on_delete=models.SET_NULL
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)

    def __str__(self):
        return f"{self.username} [{self.role}]"
