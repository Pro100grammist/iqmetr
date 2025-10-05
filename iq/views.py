import random
import json

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from .forms import StartForm
from .models import Question, Answer, TestSession, Response
from metrics.models import TestCompletion
from metrics.utils import ip_hash as ip_hash_fn

TEST_QUESTION_COUNT = 40
TEST_DURATION_SECONDS = 20 * 60  # 20 хвилин


def start(request):
    """Стартова сторінка: ім'я + вік -> redirect на правила."""
    if request.method == "POST":
        form = StartForm(request.POST)
        if form.is_valid():
            request.session["candidate"] = (
                form.cleaned_data
            )  # тимчасово у сесії браузера
            return redirect("rules")
    else:
        form = StartForm()
    return render(request, "iq/start.html", {"form": form})


def rules(request):
    """Сторінка з правилами і кнопкою 'Почати' -> створюємо TestSession і кидаємо на тест."""
    candidate = request.session.get("candidate")
    if not candidate:
        return redirect("start")
    if request.method == "POST":
        # вибираємо 30 активних питань випадково
        q_ids = list(
            Question.objects.filter(is_active=True).values_list("id", flat=True)
        )
        if len(q_ids) < TEST_QUESTION_COUNT:
            return render(
                request,
                "iq/rules.html",
                {
                    "error": "Недостатньо питань у базі.",
                    "duration": TEST_DURATION_SECONDS,
                },
            )

        # Show questions in their defined numeric order (1..N)
        selected = list(
            Question.objects.filter(is_active=True)
            .order_by("number")
            .values_list("id", flat=True)[:TEST_QUESTION_COUNT]
        )

        with transaction.atomic():
            session = TestSession.objects.create(
                name=candidate["name"],
                age=candidate["age"],
                question_ids=selected,
            )
        return redirect("test", session_uuid=session.uuid)

    return render(request, "iq/rules.html", {"duration": TEST_DURATION_SECONDS, "total": TEST_QUESTION_COUNT})


def test_view(request, session_uuid):
    """Сторінка тесту: 30 запитань з 4 відповідями, таймер, прогрес."""
    session = get_object_or_404(TestSession, uuid=session_uuid, is_completed=False)
    # обчислити скільки часу лишилось
    elapsed = (timezone.now() - session.started_at).total_seconds()
    remaining = max(0, int(TEST_DURATION_SECONDS - elapsed))
    if remaining == 0:
        return redirect("finish", session_uuid=session.uuid)

    # тягнемо питання в зафіксованому порядку
    questions = list(
        Question.objects.filter(id__in=session.question_ids).prefetch_related("answers")
    )
    # порядок як у session.question_ids:
    q_map = {q.id: q for q in questions}
    ordered_questions = [q_map[qid] for qid in session.question_ids if qid in q_map]

    if request.method == "POST":
        # ↙️ повторна перевірка, якщо пакет приповз після дедлайну
        elapsed = (timezone.now() - session.started_at).total_seconds()
        if elapsed >= TEST_DURATION_SECONDS:
            return redirect("finish", session_uuid=session.uuid)

        with transaction.atomic():
            total = Decimal("0.00")
            for q in ordered_questions:
                field = f"answer_{q.id}"
                ans_id = request.POST.get(field)
                selected = (
                    Answer.objects.filter(id=ans_id, question=q).first()
                    if ans_id
                    else None
                )
                correct = bool(selected and selected.is_correct)
                score = q.score if correct else Decimal("0.00")
                Response.objects.update_or_create(
                    session=session,
                    question=q,
                    defaults={
                        "selected_answer": selected,
                        "is_correct": correct,
                        "score_awarded": score,
                    },
                )
                total += score

            if "finish_now" in request.POST:
                session.total_score = total
                session.finished_at = timezone.now()
                session.is_completed = True
                session.save(update_fields=["total_score", "finished_at", "is_completed"])
                duration = int((session.finished_at - session.started_at).total_seconds())

                try:
                    visitor = getattr(request, "visitor", None)
                    TestCompletion.objects.create(
                        session_uuid=session.uuid,
                        visitor=visitor,
                        name=session.name,
                        age=session.age,
                        total_score=session.total_score,
                        question_count=len(session.question_ids or []),
                        started_at=session.started_at,
                        finished_at=session.finished_at,
                        duration_seconds=duration,
                        focus_loss=(session.meta or {}).get("focus_loss", 0),
                        user_agent=request.META.get("HTTP_USER_AGENT","")[:400],
                        ip_hash=ip_hash_fn(request),
                    )
                except Exception:
                    pass

                return redirect("result", session_uuid=session.uuid)

        return redirect("test", session_uuid=session.uuid)

    return render(
        request,
        "iq/test.html",
        {
            "session": session,
            "questions": ordered_questions,
            "remaining": remaining,
            "total_questions": len(ordered_questions),
        },
    )


def finish(request, session_uuid):
    """Фініш по таймеру."""
    session = get_object_or_404(TestSession, uuid=session_uuid)
    if not session.is_completed:
        # підрахунок якщо хтось нічого не обрав — 0; суму беремо з responses
        total = sum((r.score_awarded for r in session.responses.all()), Decimal("0.00"))
        session.total_score = total
        session.finished_at = timezone.now()
        session.is_completed = True
        session.save(update_fields=["total_score", "finished_at", "is_completed"])
    return redirect("result", session_uuid=session.uuid)


def result(request, session_uuid):
    """Фінальна сторінка з протоколом (де правильно/помилка по кожному питанню)."""
    session = get_object_or_404(TestSession, uuid=session_uuid)
    # дістаємо питання в вихідному порядку
    questions = list(
        Question.objects.filter(id__in=session.question_ids).prefetch_related("answers")
    )
    q_map = {q.id: q for q in questions}
    ordered_questions = [q_map[qid] for qid in session.question_ids if qid in q_map]

    # responses у dict
    resp_map = {
        r.question_id: r
        for r in session.responses.select_related("selected_answer", "question")
    }
    rows = []
    for q in ordered_questions:
        r = resp_map.get(q.id)
        rows.append(
            {
                "q": q,
                "selected": r.selected_answer if r else None,
                "is_correct": r.is_correct if r else False,
                "score": r.score_awarded if r else Decimal("0.00"),
                "correct_answer": next(
                    (a for a in q.answers.all() if a.is_correct), None
                ),
            }
        )

    return render(
        request,
        "iq/result.html",
        {
            "session": session,
            "rows": rows,
            "total": session.total_score,
        },
    )


@require_POST
def autosave(request, session_uuid):
    session = get_object_or_404(TestSession, uuid=session_uuid, is_completed=False)
    elapsed = (timezone.now() - session.started_at).total_seconds()
    if elapsed >= TEST_DURATION_SECONDS:
        return JsonResponse({"ok": False, "reason": "timeout"}, status=400)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        qid = int(payload.get("question_id"))
        aid = int(payload.get("answer_id")) if payload.get("answer_id") else None
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    q = Question.objects.filter(id=qid).first()
    if not q or q.id not in session.question_ids:
        return JsonResponse({"ok": False, "reason": "bad_question"}, status=400)

    selected = Answer.objects.filter(id=aid, question=q).first() if aid else None
    correct = bool(selected and selected.is_correct)
    score = q.score if correct else Decimal("0.00")

    with transaction.atomic():
        Response.objects.update_or_create(
            session=session,
            question=q,
            defaults={
                "selected_answer": selected,
                "is_correct": correct,
                "score_awarded": score,
            },
        )

    answered_count = session.responses.exclude(selected_answer__isnull=True).count()
    remaining = max(
        0,
        int(
            TEST_DURATION_SECONDS
            - (timezone.now() - session.started_at).total_seconds()
        ),
    )
    return JsonResponse(
        {"ok": True, "answered": answered_count, "remaining": remaining}
    )

# Override: 30-minute duration
TEST_DURATION_SECONDS = 30 * 60
