import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Visitor


@csrf_exempt
def collect(request):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False}, status=400)
    v_id = request.COOKIES.get("v_id")
    if not v_id:
        return JsonResponse({"ok": False, "err": "no_visitor"}, status=400)
    try:
        v = Visitor.objects.get(visitor_id=v_id)
    except Visitor.DoesNotExist:
        return JsonResponse({"ok": False, "err": "no_visitor"}, status=404)

    changed = False
    for fld in ("lang", "tz_offset", "screen_w", "screen_h"):
        if fld in data:
            setattr(v, fld, data[fld])
            changed = True
    if changed:
        v.save(update_fields=["lang", "tz_offset", "screen_w", "screen_h"])
    return JsonResponse({"ok": True})
