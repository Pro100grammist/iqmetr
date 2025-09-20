from django.contrib import admin
from .models import Visitor, PageView, TestCompletion


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = (
        "visitor_id",
        "first_seen",
        "last_seen",
        "is_bot",
        "lang",
        "tz_offset",
    )
    search_fields = ("visitor_id", "user_agent")


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ("visitor", "path", "ts", "referrer")
    list_filter = ("path",)


@admin.register(TestCompletion)
class TestCompletionAdmin(admin.ModelAdmin):
    list_display = ("name", "age", "total_score", "duration_seconds", "finished_at")
    search_fields = ("name",)
    list_filter = ("finished_at",)
