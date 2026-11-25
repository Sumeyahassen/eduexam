from rest_framework import serializers
from .models import Exam, Question


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["id", "type", "prompt", "answer_key", "points", "order"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        q_type = attrs.get("type") or (self.instance.type if self.instance else None)
        key = attrs.get("answer_key") or (self.instance.answer_key if self.instance else {})

        required = {
            "MCQ":   ["correct"],
            "TF":    ["correct"],
            "MATCH": ["pairs"],
            "FILL":  ["blanks"],
            "SA":    ["model_answer"],
        }
        for field in required.get(q_type, []):
            if field not in key:
                raise serializers.ValidationError(
                    {"answer_key": f"'{field}' is required for question type {q_type}."}
                )
        return attrs


class ExamSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = Exam
        fields = ["id", "title", "duration_min", "has_short_ans",
                  "is_published", "subject", "subject_name",
                  "questions", "created_at"]
        read_only_fields = ["id", "has_short_ans", "created_at"]


class ExamListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — no nested questions."""
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = Exam
        fields = ["id", "title", "duration_min", "has_short_ans",
                  "is_published", "subject", "subject_name", "created_at"]
        read_only_fields = ["id", "has_short_ans", "created_at"]
