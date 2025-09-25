# python manage.py load_practice_tasks --file=data/practice/tasks_seed.json --update
import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from practice.models import PracticalTask, Specialization

REQUIRED_BY_SPEC = {
    Specialization.CIVIL: ["intro_text", "descriptive_text", "partial_motivation_text"],
    Specialization.CRIMINAL: ["facts_text", "model_intro_text"],
}

TEXT_FIELDS = [
    "intro_text",
    "descriptive_text",
    "partial_motivation_text",
    "facts_text",
    "model_intro_text",
]


def _read_maybe_file(value: str, field_name: str, task_title: str) -> str:
    """
    Якщо value виглядає як шлях до .txt — читаємо файл з BASE_DIR.
    Інакше повертаємо значення як є.
    """
    if not isinstance(value, str):
        return value or ""

    v = value.strip()
    if not v:
        return ""

    # Якщо схоже на шлях до текстового файлу
    if v.lower().endswith(".txt"):
        p = Path(v)
        if not p.is_absolute():
            p = (Path(settings.BASE_DIR) / p).resolve()
        if not p.exists():
            raise CommandError(f"[{task_title}] file not found for {field_name}: {p}")
        try:
            text = p.read_text(encoding="utf-8")
        except Exception as e:
            raise CommandError(
                f"[{task_title}] failed to read {field_name} from {p}: {e}"
            )
        # Нормалізація перенесень рядків та зайвих пробілів по краях
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        return text

    # Інакше — це вже готовий текст у JSON
    return v


class Command(BaseCommand):
    help = "Load practical tasks from JSON list."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", required=True, help="Path to JSON file (list of tasks)."
        )
        parser.add_argument(
            "--update", action="store_true", help="Update existing (by spec+title)."
        )

    def handle(self, *args, **opts):
        p = Path(opts["file"])
        if not p.is_absolute():
            p = Path(settings.BASE_DIR) / p
        if not p.exists():
            raise CommandError(f"File not found: {p}")

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            assert isinstance(data, list)
        except Exception as e:
            raise CommandError(f"Invalid JSON: {e}")

        created = updated = skipped = 0

        for item in data:
            spec = item.get("spec")
            title = item.get("title")

            if spec not in (Specialization.CIVIL, Specialization.CRIMINAL) or not title:
                skipped += 1
                continue

            # Мінімальна валідація обов'язкових полів
            for fld in REQUIRED_BY_SPEC[spec]:
                if not item.get(fld):
                    raise CommandError(
                        f"[{title}] missing required field: {fld} for spec={spec}"
                    )

            # Підтягуємо тексти з файлів .txt
            field_values = {}
            for fld in TEXT_FIELDS:
                field_values[fld] = _read_maybe_file(item.get(fld, ""), fld, title)

            defaults = {
                "intro_text": field_values["intro_text"],
                "descriptive_text": field_values["descriptive_text"],
                "partial_motivation_text": field_values["partial_motivation_text"],
                "facts_text": field_values["facts_text"],
                "model_intro_text": field_values["model_intro_text"],
                "decisions_json": item.get("decisions_json", {}) or {},
                "is_active": bool(item.get("is_active", True)),
            }

            max_score = item.get("max_score")
            if max_score is not None:
                defaults["max_score"] = Decimal(str(max_score))

            if opts["update"]:
                obj, created_flag = PracticalTask.objects.update_or_create(
                    spec=spec, title=title, defaults=defaults
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
            else:
                obj, created_flag = PracticalTask.objects.get_or_create(
                    spec=spec, title=title, defaults=defaults
                )
                if created_flag:
                    created += 1
                else:
                    skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Tasks: created={created}, updated={updated}, skipped={skipped}"
            )
        )
