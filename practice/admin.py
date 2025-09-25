from django.contrib import admin
from .models import PracticalTask, PracticeSession, PracticeEvaluation


@admin.register(PracticalTask)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "spec", "is_active", "created_at")
    list_filter = ("spec", "is_active")
    search_fields = ("title",)


@admin.register(PracticeSession)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "spec",
        "name",
        "age",
        "is_completed",
        "started_at",
        "finished_at",
        "total_score",
    )
    list_filter = ("spec", "is_completed")
    search_fields = ("uuid", "name")


@admin.register(PracticeEvaluation)
class EvalAdmin(admin.ModelAdmin):
    list_display = ("session", "status", "total", "completed_at", "model_name")
    list_filter = ("status",)
