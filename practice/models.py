from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Specialization(models.TextChoices):
    CIVIL = "civil", "Цивільна"
    CRIMINAL = "criminal", "Кримінальна"


class PracticalTask(models.Model):
    """Датасет (заготовка практичного завдання)."""

    spec = models.CharField(max_length=16, choices=Specialization.choices)
    title = models.CharField(max_length=255)
    # Цивільна: вступна/описова/частково мотивувальна
    intro_text = models.TextField(blank=True, default="")
    descriptive_text = models.TextField(blank=True, default="")
    partial_motivation_text = models.TextField(blank=True, default="")
    # Кримінальна: фабула + модельна вступна
    facts_text = models.TextField(blank=True, default="")
    model_intro_text = models.TextField(blank=True, default="")

    # Референси рішень (повні тексти/фрагменти)
    decisions_json = models.JSONField(
        default=dict, blank=True
    )  # {"first":"...", "appeal":"...", "cassation":"..."}
    decisions_cache = models.JSONField(default=dict, blank=True)  # {"first":{"text":"...","source":"...","fetched_at":"..."}}
    decisions_last_fetch = models.DateTimeField(null=True, blank=True)

    # критерії оцінювання (через JSON)
    rubric = models.JSONField(default=dict, blank=True)
    max_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(0)],
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"[{self.get_spec_display()}] {self.title}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["spec", "title"], name="uniq_practicaltask_spec_title"
            )
        ]


class PracticeSession(models.Model):
    """Спроба"""

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    spec = models.CharField(max_length=16, choices=Specialization.choices)
    task = models.ForeignKey(PracticalTask, on_delete=models.PROTECT)

    name = models.CharField(max_length=120)
    age = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(14), MaxValueValidator(99)]
    )

    started_at = models.DateTimeField(default=timezone.now)
    deadline_at = models.DateTimeField()  # started_at + 180 хв
    finished_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    # Тексти користувача
    motivation_text = models.TextField(blank=True, default="")
    resolution_text = models.TextField(blank=True, default="")
    last_autosave_at = models.DateTimeField(null=True, blank=True)
    autosave_version = models.PositiveIntegerField(default=0)

    # Технічні лічильники
    paste_blocked = models.PositiveIntegerField(
        default=0
    )  # скільки разів ловили paste/drop
    keypress_count = models.PositiveIntegerField(default=0)

    total_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        return f"{self.uuid} ({self.get_spec_display()})"


class EvalStatus(models.TextChoices):
    PENDING = "pending", "В черзі"
    DONE = "done", "Готово"
    FAILED = "failed", "Помилка"


class PracticeEvaluation(models.Model):
    session = models.OneToOneField(
        PracticeSession, on_delete=models.CASCADE, related_name="evaluation"
    )
    status = models.CharField(
        max_length=10, choices=EvalStatus.choices, default=EvalStatus.PENDING
    )
    requested_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    model_name = models.CharField(max_length=120, blank=True, default="")
    model_params = models.JSONField(default=dict, blank=True)

    scores = models.JSONField(
        default=dict, blank=True
    )  # {"structure": 8, "law": 16, ...}
    total = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True, default="")  # узагальнений фідбек
    raw_response = models.JSONField(default=dict, blank=True)  # для аудиту

    def __str__(self):
        return f"Eval {self.session_id} [{self.status}]"
