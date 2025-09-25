from pathlib import Path
import json
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from practice.models import PracticalTask, Specialization


def validate_rubric(rubric: dict):
    """Базова валідація: суми критеріїв у групі та загальна сума = 75."""
    try:
        total_max = rubric["total_max"]
        groups = rubric["groups"]
    except Exception:
        raise CommandError("Rubric must have keys: total_max, groups")

    if total_max != 75:
        raise CommandError(f"rubric.total_max must be 75 (got {total_max})")

    sum_groups = 0
    for g in groups:
        g_key = g.get("key", "<no-key>")
        g_max = g.get("max")
        criteria = g.get("criteria", [])
        csum = sum(c.get("max", 0) for c in criteria)
        if g_max != csum:
            raise CommandError(
                f"Group '{g_key}': sum(criteria.max)={csum} != group.max={g_max}"
            )
        sum_groups += g_max

    if sum_groups != 75:
        raise CommandError(f"Sum of all groups must be 75 (got {sum_groups})")


class Command(BaseCommand):
    help = "Apply rubric JSON to all tasks of given specialization (civil/criminal)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--spec",
            required=True,
            choices=[Specialization.CIVIL, Specialization.CRIMINAL],
            help="Specialization to apply rubric to",
        )
        parser.add_argument(
            "--file",
            required=True,
            help="Path to rubric JSON file (absolute or relative to BASE_DIR)",
        )
        parser.add_argument(
            "--max",
            type=float,
            default=None,
            help="Override max_score for tasks (optional, e.g. 75)",
        )
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            help="Also apply to inactive tasks (by default only is_active=True)",
        )

    def handle(self, *args, **opts):
        spec = opts["spec"]
        path_arg = opts["file"]
        p = Path(path_arg)
        if not p.is_absolute():
            p = Path(settings.BASE_DIR) / p
        if not p.exists():
            raise CommandError(f"File not found: {p}")

        try:
            rubric = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            raise CommandError(f"Failed to read JSON: {e}")

        # Валідатор (ловить помилки до запису в БД)
        validate_rubric(rubric)

        qs = PracticalTask.objects.filter(spec=spec)
        if not opts["include_inactive"]:
            qs = qs.filter(is_active=True)

        count = 0
        override_max = opts["max"]
        for t in qs:
            t.rubric = rubric
            if override_max is not None:
                t.max_score = Decimal(str(override_max))
                t.save(update_fields=["rubric", "max_score"])
            else:
                t.save(update_fields=["rubric"])
            count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Applied rubric to {count} task(s) [spec={spec}, active_only={not opts['include_inactive']}]"
            )
        )
