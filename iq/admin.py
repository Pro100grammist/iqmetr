from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from .models import Question, Answer, TestSession, Response


class AnswerInlineFormset(BaseInlineFormSet):
    def clean(self):
        super().clean()
        not_deleted = [f for f in self.forms if not f.cleaned_data.get("DELETE", False)]
        total = len(not_deleted)
        correct = sum(1 for f in not_deleted if f.cleaned_data.get("is_correct"))
        if total != 4:
            raise ValidationError("Має бути рівно 4 варіанти відповіді.")
        if correct != 1:
            raise ValidationError("Має бути рівно 1 правильна відповідь.")


class AnswerInline(admin.TabularInline):
    model = Answer
    formset = AnswerInlineFormset
    extra = 4
    min_num = 4
    max_num = 4
    validate_min = True
    validate_max = True
    can_delete = True


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
