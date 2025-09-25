import json
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import PracticeSession, PracticeEvaluation, EvalStatus
from .services.eval import call_ai_evaluator


@require_POST
def autosave(request, session_uuid):
    s = get_object_or_404(PracticeSession, uuid=session_uuid)
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False}, status=400)

    s.motivation_text = data.get("motivation_text", s.motivation_text)
    s.resolution_text = data.get("resolution_text", s.resolution_text)
    s.keypress_count = int(data.get("keypress_count", s.keypress_count) or 0)
    s.paste_blocked += int(data.get("paste_event", 0))
    s.autosave_version += 1
    s.last_autosave_at = timezone.now()
    s.save(
        update_fields=[
            "motivation_text",
            "resolution_text",
            "keypress_count",
            "paste_blocked",
            "autosave_version",
            "last_autosave_at",
        ]
    )
    return JsonResponse({"ok": True, "ver": s.autosave_version})


@require_POST
def evaluate_now(request, session_uuid):
    s = get_object_or_404(PracticeSession, uuid=session_uuid)
    ev, _ = PracticeEvaluation.objects.get_or_create(session=s)
    # Дозволяємо повторний запуск і після "failed"/"done": переведемо у pending і запустимо
    if ev.status != EvalStatus.PENDING:
        ev.status = EvalStatus.PENDING
        ev.requested_at = timezone.now()
        ev.completed_at = None
        ev.save(update_fields=["status", "requested_at", "completed_at"])
    try:
        call_ai_evaluator(s, ev)  # змінює ev.status/total/scores/feedback
    except Exception as e:
        ev.status = EvalStatus.FAILED
        ev.save(update_fields=["status"])
        return JsonResponse({"ok": False, "err": str(e)}, status=500)
    return JsonResponse(
        {"ok": True, "status": ev.status, "total": ev.total, "scores": ev.scores}
    )
