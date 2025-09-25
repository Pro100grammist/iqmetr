# practice/management/commands/ingest_decisions.py
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from practice.models import PracticalTask
from practice.services.decisions import load_txt, _now_iso


class Command(BaseCommand):
    help = "Read decisions from local TXT files in decisions_json and cache into decisions_cache."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, help="PracticalTask id (optional)")
        parser.add_argument(
            "--spec", choices=["civil", "criminal"], help="Filter by spec (optional)"
        )
        parser.add_argument(
            "--refetch", action="store_true", help="Force re-read even if cached"
        )

    def handle(self, *args, **opts):
        qs = PracticalTask.objects.all()
        if opts.get("id"):
            qs = qs.filter(id=opts["id"])
        if opts.get("spec"):
            qs = qs.filter(spec=opts["spec"])

        total, ingested = 0, 0
        for t in qs:
            total += 1
            links = t.decisions_json or {}
            cache = t.decisions_cache or {}
            changed = False

            for key in ("first", "appeal", "cassation"):
                src = links.get(key)
                if not src:
                    continue
                has = cache.get(key, {}).get("text")
                if has and not opts["refetch"]:
                    continue
                try:
                    text = load_txt(src, settings.BASE_DIR)
                    cache[key] = {
                        "type": "file-txt",
                        "text": text,
                        "source": src,
                        "fetched_at": _now_iso(),
                    }
                    ingested += 1
                    changed = True
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f"[{t.id}] {key}: {e}"))

            if changed:
                t.decisions_cache = cache
                t.decisions_last_fetch = timezone.now()
                t.save(update_fields=["decisions_cache", "decisions_last_fetch"])

        self.stdout.write(self.style.SUCCESS(f"Scanned {total}, ingested {ingested}"))
