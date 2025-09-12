# iq/admin.py
from django.contrib import admin
from .models import Question, Answer, TestSession, Response


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("number", "difficulty", "score", "is_active")
    list_filter = ("difficulty", "is_active")
    search_fields = ("text",)
    inlines = [AnswerInline]


@admin.register(TestSession)
class TestSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "age", "started_at", "is_completed", "total_score")


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("session", "question", "is_correct", "score_awarded")
