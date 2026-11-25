import csv
import io

import openpyxl
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from tenants.permissions import IsInstAdmin, IsExaminer
from tenants.mixins import TenantScopeMixin
from .models import AcademicYear, SubjectOrCourse, Student
from .serializers import (
    AcademicYearSerializer,
    SubjectOrCourseSerializer,
    StudentSerializer,
    StudentBulkSerializer,
)


class AcademicYearViewSet(TenantScopeMixin, viewsets.ModelViewSet):
    serializer_class = AcademicYearSerializer
    permission_classes = [IsInstAdmin]

    def get_queryset(self):
        return AcademicYear.objects.filter(institution=self.get_institution())


class SubjectOrCourseViewSet(TenantScopeMixin, viewsets.ModelViewSet):
    serializer_class = SubjectOrCourseSerializer
    permission_classes = [IsExaminer]

    def get_queryset(self):
        qs = SubjectOrCourse.objects.filter(
            institution=self.get_institution()
        ).prefetch_related("students")
        year = self.request.query_params.get("year")
        if year:
            qs = qs.filter(academic_year__label=year)
        return qs


class StudentViewSet(TenantScopeMixin, viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    permission_classes = [IsInstAdmin]

    def get_queryset(self):
        return Student.objects.filter(
            institution=self.get_institution()
        ).prefetch_related("enrollments")

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """POST JSON: {"students": [{student_id, full_name, ...}]}"""
        serializer = StudentBulkSerializer(
            data=request.data,
            context={"institution": self.get_institution()},
        )
        serializer.is_valid(raise_exception=True)
        created = serializer.save()
        return Response({"imported": len(created)}, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["post"],
        url_path="upload-file",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_file(self, request):
        """
        POST multipart/form-data with field 'file' (.csv or .xlsx).
        CSV/Excel columns: student_id, full_name, access_pin (optional)
        """
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"detail": "No file provided. Send a 'file' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        filename = file_obj.name.lower()
        rows = []

        if filename.endswith(".csv"):
            try:
                text = file_obj.read().decode("utf-8-sig")  # handle BOM
                reader = csv.DictReader(io.StringIO(text))
                rows = list(reader)
            except Exception as e:
                return Response({"detail": f"CSV parse error: {e}"},
                                status=status.HTTP_400_BAD_REQUEST)

        elif filename.endswith((".xlsx", ".xls")):
            try:
                wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
                ws = wb.active
                headers = [str(c.value).strip() if c.value else "" for c in next(ws.iter_rows())]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    rows.append({headers[i]: (str(v).strip() if v is not None else "")
                                 for i, v in enumerate(row)})
            except Exception as e:
                return Response({"detail": f"Excel parse error: {e}"},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {"detail": "Unsupported file type. Upload a .csv or .xlsx file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        institution = self.get_institution()
        imported, errors = [], []

        for i, row in enumerate(rows, start=2):
            student_id = str(row.get("student_id", "")).strip()
            full_name  = str(row.get("full_name", "")).strip()
            access_pin = str(row.get("access_pin", "")).strip()

            if not student_id or not full_name:
                errors.append(f"Row {i}: student_id and full_name are required.")
                continue

            student, _ = Student.objects.update_or_create(
                institution=institution,
                student_id=student_id,
                defaults={
                    "full_name": full_name,
                    "access_pin": access_pin,
                    "institution": institution,
                },
            )
            imported.append(student)

        return Response(
            {"imported": len(imported), "errors": errors},
            status=status.HTTP_201_CREATED,
        )
