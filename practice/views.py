from decimal import Decimal
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models.functions import Random

from .models import (
    PracticalTask,
    PracticeSession,
    PracticeEvaluation,
    Specialization,
    EvalStatus,
)
from .constants import CIVIL_MOTIVATION_TEMPLATE, CIVIL_RESOLUTION_TEMPLATE
from .utils import compile_final_document


DURATION_MIN = 180  # хвилин


def index(request):
    # проста сторінка з кнопками CIVIL / CRIMINAL
    return render(request, "practice/index.html")


def start_session(request, spec):
    if spec not in (Specialization.CIVIL, Specialization.CRIMINAL):
        return redirect("practice_index")

    # тут береться ім'я/вік із форми або із попереднього екрану (можеш переюзати вашу Start форму)
    name = request.POST.get("name") or request.GET.get("name") or "Учасник"
    age = int(request.POST.get("age") or request.GET.get("age") or 0) or 18

    task = (
        PracticalTask.objects.filter(spec=spec, is_active=True)
        .order_by(Random())
        .first()
    )
    if not task:
        return render(
            request,
            "practice/error.html",
            {"msg": "Нема активних завдань для цієї спец."},
        )

    now = timezone.now()
    session = PracticeSession.objects.create(
        spec=spec,
        task=task,
        name=name,
        age=age,
        started_at=now,
        deadline_at=now + timedelta(minutes=DURATION_MIN),
    )
    # якщо це цивільна справа, то додаємо шаблони в мотивацію/резолюцію
    if session.spec == Specialization.CIVIL:
        touched = False
        if not (session.motivation_text or "").strip():
            session.motivation_text = CIVIL_MOTIVATION_TEMPLATE
            touched = True
        if not (session.resolution_text or "").strip():
            session.resolution_text = CIVIL_RESOLUTION_TEMPLATE
            touched = True
        if touched:
            session.save(update_fields=["motivation_text", "resolution_text"])

    return redirect("practice_editor", session_uuid=session.uuid)


def editor(request, session_uuid):
    s = get_object_or_404(PracticeSession, uuid=session_uuid)

    if s.spec == Specialization.CIVIL:
        touched = False
        if not (s.motivation_text or "").strip():
            s.motivation_text = CIVIL_MOTIVATION_TEMPLATE
            touched = True
        if not (s.resolution_text or "").strip():
            s.resolution_text = CIVIL_RESOLUTION_TEMPLATE
            touched = True
        if touched:
            s.save(update_fields=["motivation_text", "resolution_text"])

    now = timezone.now()
    remaining = max(0, int((s.deadline_at - now).total_seconds()))
    if s.is_completed:
        return redirect("practice_result", session_uuid=s.uuid)
    return render(
        request,
        "practice/editor.html",
        {
            "s": s,
            "task": s.task,
            "remaining": remaining,
            "duration_min": DURATION_MIN,
        },
    )


def finish(request, session_uuid):
    s = get_object_or_404(PracticeSession, uuid=session_uuid)
    if s.is_completed:
        return redirect("practice_result", session_uuid=s.uuid)
    # Save latest textarea contents from the submitted form (fallback to autosave)
    if request.method == "POST":
        mot = request.POST.get("motivation")
        res = request.POST.get("resolution")
        update_fields = []
        if mot is not None:
            s.motivation_text = mot
            update_fields.append("motivation_text")
        if res is not None:
            s.resolution_text = res
            update_fields.append("resolution_text")
        if update_fields:
            s.save(update_fields=update_fields)

    s.finished_at = timezone.now()
    s.is_completed = True
    s.save(update_fields=["finished_at", "is_completed"])

    # створюємо заготовку на оцінювання (можна одразу викликати API)
    PracticeEvaluation.objects.get_or_create(session=s, defaults={})
    return redirect("practice_result", session_uuid=s.uuid)


def result(request, session_uuid):
    s = get_object_or_404(PracticeSession, uuid=session_uuid)
    ev = getattr(s, "evaluation", None)
    return render(
        request,
        "practice/result.html",
        {"s": s, "ev": ev},
    )


def result(request, session_uuid):
    s = get_object_or_404(PracticeSession, uuid=session_uuid)

    # зібраний фінальний документ
    compiled = compile_final_document(s)

    # (опційно) скільки часу витрачено
    elapsed_sec = None
    if s.started_at and s.finished_at:
        elapsed_sec = int((s.finished_at - s.started_at).total_seconds())

    ev = getattr(s, "evaluation", None)
    return render(
        request,
        "practice/result.html",
        {
            "s": s,
            "ev": ev,
            "compiled": compiled,
            "elapsed_sec": elapsed_sec,
        },
    )
