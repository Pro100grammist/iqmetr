from django.core.management.base import BaseCommand, CommandError
from iq.models import Question, Answer
import json
from decimal import Decimal


class Command(BaseCommand):
    help = "Load questions from JSON file"

    def add_arguments(self, parser):
        parser.add_argument("path", type=str)

    def handle(self, *args, **opts):
        path = opts["path"]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        created_q = 0
        Question.objects.all().delete()
        for item in data:
            q = Question.objects.create(
                number=item["number"],
                text=item["text"],
                difficulty=item["difficulty"],
                score=Decimal(item.get("score", "1.22")),
                is_active=item.get("is_active", True),
            )
            for a in item["answers"]:
                Answer.objects.create(
                    question=q,
                    text=a["text"],
                    is_correct=bool(a.get("is_correct", False)),
                )
            created_q += 1

        self.stdout.write(self.style.SUCCESS(f"Loaded {created_q} questions"))
