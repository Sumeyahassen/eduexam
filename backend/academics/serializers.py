from rest_framework import serializers
from .models import AcademicYear, SubjectOrCourse, Student


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ["id", "label", "is_active"]
        read_only_fields = ["id"]


class SubjectOrCourseSerializer(serializers.ModelSerializer):
    academic_year_label = serializers.CharField(
        source="academic_year.label", read_only=True
    )
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = SubjectOrCourse
        fields = ["id", "name", "code", "level_or_dept",
                  "academic_year", "academic_year_label", "student_count"]
        read_only_fields = ["id"]

    def get_student_count(self, obj):
        return obj.students.count()


class StudentSerializer(serializers.ModelSerializer):
    enrollments = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=SubjectOrCourse.objects.all(),
        required=False,
    )
    enrollment_names = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ["id", "student_id", "full_name", "enrollments",
                  "enrollment_names", "access_pin"]
        read_only_fields = ["id", "enrollment_names"]
        extra_kwargs = {"access_pin": {"write_only": True}}

    def get_enrollment_names(self, obj):
        return [s.name for s in obj.enrollments.all()]


class StudentBulkSerializer(serializers.Serializer):
    """Accepts a list of student dicts for JSON bulk import."""
    students = StudentSerializer(many=True)

    def create(self, validated_data):
        institution = self.context["institution"]
        created = []
        for item in validated_data["students"]:
            enrollments = item.pop("enrollments", [])
            item.pop("enrollment_names", None)
            student, _ = Student.objects.update_or_create(
                institution=institution,
                student_id=item["student_id"],
                defaults={**item, "institution": institution},
            )
            if enrollments:
                student.enrollments.set(enrollments)
            created.append(student)
        return created
