# iq/models.py
from django.db import models
from django.utils import timezone
import uuid
from decimal import Decimal


class Question(models.Model):
    DIFF_EASY = "easy"
    DIFF_MEDIUM = "medium"
    DIFF_HARD = "hard"
    DIFFICULTY_CHOICES = [
        (DIFF_EASY, "Просте"),
        (DIFF_MEDIUM, "Середнє"),
        (DIFF_HARD, "Складне"),
    ]

    number = models.PositiveIntegerField()
    text = models.TextField()
    # New: question type and image support
    TYPE_VERBAL = "verbal"
    TYPE_LOGICAL = "logical"
    TYPE_ABSTRACT = "abstract"
    TASK_TYPE_CHOICES = [
        (TYPE_VERBAL, "verbal"),
        (TYPE_LOGICAL, "logical"),
        (TYPE_ABSTRACT, "abstract"),
    ]
    task_type = models.CharField(max_length=10, choices=TASK_TYPE_CHOICES, default=TYPE_VERBAL)
    image_url = models.CharField(max_length=500, blank=True, default="")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.22"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"#{self.number} {self.text[:50]}"


class Answer(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers"
    )
    text = models.CharField(max_length=500, blank=True, default="")
    image_url = models.CharField(max_length=500, blank=True, default="")
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Q{self.question.number}: {self.text[:50]}"


class TestSession(models.Model):
    """
    Сесія тесту на 30 запитань, 20 хвилин. Поки триває — балів не показуємо.
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=120)
    age = models.PositiveSmallIntegerField()
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    total_score = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0.00")
    )
    is_completed = models.BooleanField(default=False)

    # збережемо список вибраних питань (id) у фіксованому порядку
    question_ids = models.JSONField(default=list)

    def __str__(self):
        return f"{self.name} ({self.age}) [{self.uuid}]"


class Response(models.Model):
    session = models.ForeignKey(
        TestSession, on_delete=models.CASCADE, related_name="responses"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(
        Answer, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_correct = models.BooleanField(default=False)
    score_awarded = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00")
    )

    class Meta:
        unique_together = ("session", "question")
