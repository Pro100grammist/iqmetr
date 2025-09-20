from django.db import models
from django.utils import timezone
import uuid


class Visitor(models.Model):
    """Унікальний відвідувач сайту (за першим-party cookie)."""

    visitor_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)
    ip_hash = models.CharField(max_length=128, blank=True, default="")  # SHA256 з сіллю
    user_agent = models.TextField(blank=True, default="")
    initial_referrer = models.TextField(blank=True, default="")
    lang = models.CharField(max_length=32, blank=True, default="")
    tz_offset = models.IntegerField(null=True, blank=True)  # хвилини різниці з UTC
    screen_w = models.IntegerField(null=True, blank=True)
    screen_h = models.IntegerField(null=True, blank=True)
    is_bot = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.visitor_id}"


class PageView(models.Model):
    visitor = models.ForeignKey(Visitor, null=True, on_delete=models.SET_NULL)
    path = models.TextField()
    referrer = models.TextField(blank=True, default="")
    ts = models.DateTimeField(default=timezone.now)
    method = models.CharField(max_length=8, default="GET")


class TestCompletion(models.Model):
    """Зліпок результату складання тесту (для метрик)."""

    # Можемо тримати FK на вашу сесію, якщо є
    session_uuid = models.UUIDField(null=True, blank=True)
    visitor = models.ForeignKey(Visitor, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    age = models.PositiveSmallIntegerField()
    total_score = models.DecimalField(max_digits=6, decimal_places=2)
    question_count = models.PositiveSmallIntegerField()
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField()
    duration_seconds = models.PositiveIntegerField()
    focus_loss = models.IntegerField(default=0)
    user_agent = models.TextField(blank=True, default="")
    ip_hash = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
