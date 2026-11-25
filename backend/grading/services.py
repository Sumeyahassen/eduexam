"""
Auto-grading and manual review logic.
Kept in a service module so views stay thin and logic is testable.
"""
from django.utils import timezone

from exams.models import Question
from .models import ExamAttempt, StudentAnswer


def auto_grade_attempt(attempt: ExamAttempt) -> None:
    """
    Score all objective questions in the attempt.
    Set status to NEEDS_MANUAL if any Short Answer questions exist,
    otherwise FINALIZED.
    """
    total = 0.0

    for answer in attempt.answers.select_related("question"):
        q = answer.question

        if q.type == Question.Type.SHORT_ANSWER:
            # Short answers are left unscored — examiner will fill them in
            continue

        awarded = _score_objective(q, answer.response_data)
        answer.points_awarded = awarded
        answer.reviewed = True
        answer.save(update_fields=["points_awarded", "reviewed"])
        total += awarded

    attempt.auto_score = total
    attempt.status = (
        ExamAttempt.Status.NEEDS_MANUAL
        if attempt.exam.has_short_ans
        else ExamAttempt.Status.FINALIZED
    )
    if attempt.status == ExamAttempt.Status.FINALIZED:
        attempt.final_score = total
    attempt.submitted_at = timezone.now()
    attempt.save(update_fields=["auto_score", "status", "final_score", "submitted_at"])


def _score_objective(question: Question, response_data: dict) -> float:
    q_type = question.type
    key = question.answer_key

    if q_type in (Question.Type.MCQ, Question.Type.TRUE_FALSE):
        correct = key.get("correct")
        given = response_data.get("selected")
        return question.points if correct == given else 0.0

    if q_type == Question.Type.MATCHING:
        correct_pairs = {tuple(p) for p in key.get("pairs", [])}
        given_pairs = {tuple(p) for p in response_data.get("pairs", [])}
        if not correct_pairs:
            return 0.0
        ratio = len(correct_pairs & given_pairs) / len(correct_pairs)
        return round(question.points * ratio, 2)

    if q_type == Question.Type.FILL_BLANK:
        correct_blanks = [str(b).strip().lower() for b in key.get("blanks", [])]
        given_blanks = [str(b).strip().lower() for b in response_data.get("blanks", [])]
        if not correct_blanks:
            return 0.0
        matches = sum(
            1 for c, g in zip(correct_blanks, given_blanks) if c == g
        )
        ratio = matches / len(correct_blanks)
        return round(question.points * ratio, 2)

    return 0.0


def finalize_manual_review(attempt: ExamAttempt) -> None:
    """
    Called by the examiner after scoring all Short Answer responses.
    Sums auto_score + manually awarded SA points and marks attempt FINALIZED.
    """
    sa_total = (
        attempt.answers
        .filter(question__type=Question.Type.SHORT_ANSWER)
        .exclude(points_awarded=None)
        .values_list("points_awarded", flat=True)
    )
    manual_total = sum(sa_total)
    attempt.manual_score = manual_total
    attempt.final_score = (attempt.auto_score or 0) + manual_total
    attempt.status = ExamAttempt.Status.FINALIZED
    attempt.save(update_fields=["manual_score", "final_score", "status"])
